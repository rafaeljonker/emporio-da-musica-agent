"""Runs one turn through the graph and measures it (research §9)."""

import logging
from collections.abc import Callable
from decimal import Decimal
from time import perf_counter

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from emporio.platform.config import Provider, Settings
from emporio.support.application.handle_message import CHAT_ERROR
from emporio.support.application.ports import TurnMetrics
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.cost import turn_cost_brl
from emporio.support.infrastructure.agent.graph import AgentGraph
from emporio.support.infrastructure.agent.turn_probe import TurnProbe, to_ms
from emporio.support.infrastructure.tracing import TracerFactory

logger = logging.getLogger("emporio.support.runner")


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
        return turn_cost_brl(self._settings, model, self._guard_model(model), probe)

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
            ms_total=to_ms(perf_counter() - started),
            ms_guard=to_ms(probe.ms_guard),
            ms_llm=to_ms(probe.ms_llm),
            ms_tools=to_ms(probe.ms_tools),
            cost_brl=self._cost_brl(model, probe),
            trace_id=trace_id,
            failed=failed,
        )
        return answer, scope, metrics
