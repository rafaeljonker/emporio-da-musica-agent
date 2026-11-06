"""Runs one turn through the graph and measures it (research §9)."""

import logging
from collections.abc import Callable
from decimal import Decimal
from threading import Lock
from time import perf_counter
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import LLMResult
from langgraph.errors import GraphRecursionError

from emporio.config import Provider, Settings
from emporio.support.application.handle_message import CHAT_ERROR
from emporio.support.application.ports import TurnMetrics
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.graph import AgentGraph
from emporio.support.infrastructure.tracing import TracerFactory

logger = logging.getLogger("emporio.support.runner")


def _ms(seconds: float) -> int:
    return round(seconds * 1000)


def _usd(
    price: tuple[Decimal, Decimal, Decimal], input_tokens: int, cached: int, output: int
) -> Decimal:
    usd_in, usd_out, usd_cached = price
    fresh = input_tokens - cached
    return (fresh * usd_in + cached * usd_cached + output * usd_out) / Decimal(1_000_000)


class TurnProbe(BaseCallbackHandler):
    """Per-turn timings, model calls, token usage and tool names, read from callbacks.

    Callbacks also see the guard's classifier call, which never reaches graph state.
    Tools of one message run in parallel, so `ms_tools` sums their durations. LLM time spent
    inside the guard counts only in `ms_guard`, so ms_guard + ms_llm + ms_tools is roughly
    at most ms_total (parallel tools can exceed it). Callbacks may fire from tool threads,
    so every update takes one lock.
    """

    def __init__(self) -> None:
        self._started: dict[UUID, float] = {}
        self.llm_calls = 0
        self.ms_llm = 0.0
        self.ms_tools = 0.0
        self.ms_guard = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        # Share of the totals above spent by the guard (priced at the guard model).
        self.guard_input_tokens = 0
        self.guard_output_tokens = 0
        self.guard_cached_tokens = 0
        self.tools: list[str] = []
        self._guard_runs: set[UUID] = set()
        self._parents: dict[UUID, UUID | None] = {}
        self._lock = Lock()

    def _in_guard(self, run_id: UUID | None) -> bool:
        while run_id is not None:
            if run_id in self._guard_runs:
                return True
            run_id = self._parents.get(run_id)
        return False

    def _start(self, run_id: UUID) -> None:
        self._started[run_id] = perf_counter()

    def _elapsed(self, run_id: UUID) -> float:
        return perf_counter() - self._started.pop(run_id, perf_counter())

    def on_chain_start(
        self,
        serialized: dict[str, object] | None,
        inputs: object,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id
            if kwargs.get("name") == "guard":
                self._guard_runs.add(run_id)
                self._start(run_id)

    def on_chain_end(
        self, outputs: object, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: object
    ) -> None:
        with self._lock:
            if run_id in self._guard_runs:
                self.ms_guard += self._elapsed(run_id)

    def on_chat_model_start(
        self,
        serialized: dict[str, object] | None,
        messages: object,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id
            self.llm_calls += 1
            self._start(run_id)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            elapsed = self._elapsed(run_id)
            in_guard = self._in_guard(self._parents.get(run_id))
            if not in_guard:
                self.ms_llm += elapsed
            for generation in response.generations[0][:1]:
                message = getattr(generation, "message", None)
                usage = message.usage_metadata if isinstance(message, AIMessage) else None
                if usage:
                    cached = (usage.get("input_token_details") or {}).get("cache_read", 0)
                    self.input_tokens += usage["input_tokens"]
                    self.output_tokens += usage["output_tokens"]
                    self.cached_tokens += cached
                    if in_guard:
                        self.guard_input_tokens += usage["input_tokens"]
                        self.guard_output_tokens += usage["output_tokens"]
                        self.guard_cached_tokens += cached

    def on_tool_start(
        self,
        serialized: dict[str, object] | None,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self.tools.append(str(kwargs.get("name") or (serialized or {}).get("name")))
            self._start(run_id)

    def on_tool_end(
        self, output: object, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: object
    ) -> None:
        with self._lock:
            self.ms_tools += self._elapsed(run_id)


class GraphRunner:
    def __init__(
        self,
        graph: AgentGraph,
        settings: Settings,
        tracer_factory: TracerFactory,
        customer_name: Callable[[int], str | None],
    ) -> None:
        self._graph = graph
        self._settings = settings
        self._tracer_factory = tracer_factory
        self._customer_name = customer_name

    def _model(self) -> str:
        s = self._settings
        if s.fake_model:
            return "scripted"
        return {
            Provider.GEMMA: s.gemma_model,
            Provider.GEMINI: s.gemini_model,
            Provider.OPENAI: s.openai_model,
            Provider.ANTHROPIC: s.anthropic_model,
            Provider.LOCAL: s.ollama_model,
        }[s.provider]

    def _guard_model(self, model: str) -> str:
        s = self._settings
        if s.fake_model or s.provider is not Provider.GEMINI:
            return model
        return s.gemini_guard_model

    def _cost_brl(self, model: str, probe: TurnProbe) -> Decimal | None:
        price = self._settings.prices.get(model)
        if price is None:
            gpu = self._settings.gpu_usd_per_hour
            if gpu is None or self._settings.provider_name != Provider.GEMMA.value:
                return None
            # Upper bound: assumes the GPU served only this turn (concurrency 1).
            ms = Decimal(_ms(probe.ms_guard) + _ms(probe.ms_llm))
            return gpu * ms / 3_600_000 * self._settings.usd_brl
        guard_price = self._settings.prices.get(self._guard_model(model), price)
        agent_usd = _usd(
            price,
            probe.input_tokens - probe.guard_input_tokens,
            probe.cached_tokens - probe.guard_cached_tokens,
            probe.output_tokens - probe.guard_output_tokens,
        )
        guard_usd = _usd(
            guard_price,
            probe.guard_input_tokens,
            probe.guard_cached_tokens,
            probe.guard_output_tokens,
        )
        return (agent_usd + guard_usd) * self._settings.usd_brl

    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]:
        started = perf_counter()
        probe = TurnProbe()
        trace_id = ""
        answer, scope = CHAT_ERROR, Scope.LOJA
        failed = True
        try:
            callbacks, trace_id = self._tracer_factory.for_turn(identity)
            name = (
                None if identity.customer_id is None else self._customer_name(identity.customer_id)
            )
            context = TurnContext(identity.customer_id, name, self._settings.store_today)
            config = {
                "configurable": {"thread_id": identity.thread_id()},
                "callbacks": [*callbacks, probe],
                "metadata": self._tracer_factory.turn_metadata(identity),
            }
            result = self._graph.invoke(
                {"messages": [HumanMessage(text)]},
                config,  # pyright: ignore[reportArgumentType]  # plain dict is a valid RunnableConfig
                context=context,
            )
            scope = Scope(result["scope"])
            answer = result["messages"][-1].text.strip()
            if not answer:
                logger.warning("model produced an empty final answer")
                answer = CHAT_ERROR
            else:
                failed = False
        except GraphRecursionError:
            logger.exception("turn hit the graph recursion limit")
        except Exception:
            logger.exception("turn failed")
        model = self._model()
        metrics = TurnMetrics(
            thread_id=identity.thread_id(),
            provider=self._settings.provider_name,
            model=model,
            scope=scope,
            input_tokens=probe.input_tokens,
            output_tokens=probe.output_tokens,
            cached_tokens=probe.cached_tokens,
            llm_calls=probe.llm_calls,
            tools=tuple(sorted(probe.tools)),
            ms_total=_ms(perf_counter() - started),
            ms_guard=_ms(probe.ms_guard),
            ms_llm=_ms(probe.ms_llm),
            ms_tools=_ms(probe.ms_tools),
            cost_brl=self._cost_brl(model, probe),
            trace_id=trace_id,
            failed=failed,
        )
        return answer, scope, metrics
