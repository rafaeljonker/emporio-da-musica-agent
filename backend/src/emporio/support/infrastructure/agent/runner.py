"""Runs one turn through the graph and measures it (research §9)."""

import logging
from collections.abc import Callable
from decimal import Decimal
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


class TurnProbe(BaseCallbackHandler):
    """Per-turn timings, model calls, token usage and tool names, read from callbacks.

    Callbacks also see the guard's classifier call, which never reaches graph state.
    Tools of one message run in parallel, so `ms_tools` sums their durations.
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
        self.tools: list[str] = []
        self._guard_runs: set[UUID] = set()

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
        **kwargs: object,
    ) -> None:
        if kwargs.get("name") == "guard":
            self._guard_runs.add(run_id)
            self._start(run_id)

    def on_chain_end(self, outputs: object, *, run_id: UUID, **kwargs: object) -> None:
        if run_id in self._guard_runs:
            self.ms_guard += self._elapsed(run_id)

    def on_chat_model_start(
        self,
        serialized: dict[str, object] | None,
        messages: object,
        *,
        run_id: UUID,
        **kwargs: object,
    ) -> None:
        self.llm_calls += 1
        self._start(run_id)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: object) -> None:
        self.ms_llm += self._elapsed(run_id)
        for generation in response.generations[0][:1]:
            message = getattr(generation, "message", None)
            usage = message.usage_metadata if isinstance(message, AIMessage) else None
            if usage:
                self.input_tokens += usage["input_tokens"]
                self.output_tokens += usage["output_tokens"]
                details = usage.get("input_token_details") or {}
                self.cached_tokens += details.get("cache_read", 0)

    def on_tool_start(
        self,
        serialized: dict[str, object] | None,
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: object,
    ) -> None:
        self.tools.append(str(kwargs.get("name") or (serialized or {}).get("name")))
        self._start(run_id)

    def on_tool_end(self, output: object, *, run_id: UUID, **kwargs: object) -> None:
        self.ms_tools += self._elapsed(run_id)


class GraphRunner:
    def __init__(
        self,
        graph: AgentGraph,
        settings: Settings,
        tracer_factory: TracerFactory,
        customer_name: Callable[[int], str | None] = lambda _id: None,
    ) -> None:
        self._graph = graph
        self._settings = settings
        self._tracer_factory = tracer_factory
        self._customer_name = customer_name

    def _model(self) -> str:
        s = self._settings
        return {
            Provider.GEMMA: s.gemma_model,
            Provider.GEMINI: s.gemini_model,
            Provider.OPENAI: s.openai_model,
            Provider.ANTHROPIC: s.anthropic_model,
        }[s.provider]

    def _cost_brl(self, model: str, probe: TurnProbe) -> Decimal | None:
        price = self._settings.prices.get(model)
        if price is None:
            return None
        usd = (probe.input_tokens * price[0] + probe.output_tokens * price[1]) / Decimal(1_000_000)
        return usd * self._settings.usd_brl

    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]:
        callbacks, trace_id = self._tracer_factory.for_turn(identity)
        probe = TurnProbe()
        name = None if identity.customer_id is None else self._customer_name(identity.customer_id)
        context = TurnContext(identity.customer_id, name, self._settings.store_today)
        config = {
            "configurable": {"thread_id": identity.thread_id()},
            "callbacks": [*callbacks, probe],
        }
        started = perf_counter()
        answer, scope = CHAT_ERROR, Scope.LOJA
        try:
            result = self._graph.invoke(
                {"messages": [HumanMessage(text)]},
                config,  # pyright: ignore[reportArgumentType]  # plain dict is a valid RunnableConfig
                context=context,
            )
            answer, scope = result["messages"][-1].text, result["scope"]
        except GraphRecursionError:
            logger.exception("turn hit the graph recursion limit")
        except Exception:
            logger.exception("turn failed")
        model = self._model()
        metrics = TurnMetrics(
            thread_id=identity.thread_id(),
            provider=self._settings.provider.value,
            model=model,
            scope=scope,
            input_tokens=probe.input_tokens,
            output_tokens=probe.output_tokens,
            cached_tokens=probe.cached_tokens,
            llm_calls=probe.llm_calls,
            tools=tuple(probe.tools),
            ms_total=_ms(perf_counter() - started),
            ms_guard=_ms(probe.ms_guard),
            ms_llm=_ms(probe.ms_llm),
            ms_tools=_ms(probe.ms_tools),
            cost_brl=self._cost_brl(model, probe),
            trace_id=trace_id,
        )
        return answer, scope, metrics
