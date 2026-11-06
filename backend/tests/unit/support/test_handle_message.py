import time
from decimal import Decimal

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError

from emporio.config import Settings
from emporio.support.application.handle_message import CHAT_ERROR, HandleMessage
from emporio.support.application.ports import TurnMetrics
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.graph import AgentGraph, build_graph
from emporio.support.infrastructure.agent.runner import GraphRunner, TurnProbe
from emporio.support.infrastructure.agent.tools import build_tools
from tests.fakes.fake_chat_model import FakeToolCallingModel
from tests.fakes.recording_tracer import RecordingTracer
from tests.unit.support.test_tools import make_box

SETTINGS = Settings(_env_file=None, store_today="2026-02-20")  # pyright: ignore[reportCallIssue]
ANON = ChannelIdentity("web", None, "s1")


def no_name(_id: int) -> str | None:
    return None


def _metrics(trace_id: str = "t-1") -> TurnMetrics:
    return TurnMetrics(
        "web:anon:s1", "gemma", "m", Scope.LOJA, 1, 1, 0, 1, (), 5, 1, 2, 0, None, trace_id
    )


class FakeRunner:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[str] = []

    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]:
        self.calls.append(text)
        return self.answer, Scope.LOJA, _metrics()


class FakeStore:
    def __init__(self) -> None:
        self.saved: list[TurnMetrics] = []

    def save(self, m: TurnMetrics) -> None:
        self.saved.append(m)


def test_handle_message_returns_bubbles_and_saves_metrics() -> None:
    runner, store = FakeRunner("Temos sim.\n\nQuer ver?"), FakeStore()
    reply = HandleMessage(runner, store)(ANON, "tem violão?")
    assert reply.bubbles == ("Temos sim.", "Quer ver?")
    assert reply.scope is Scope.LOJA
    assert reply.trace_id == "t-1"
    assert reply.tells == ()
    assert store.saved == [_metrics()]


def test_reply_reports_ai_tells() -> None:
    reply = HandleMessage(FakeRunner("Ótima pergunta!"), FakeStore())(ANON, "oi")
    assert reply.tells


def test_blank_message_short_circuits() -> None:
    runner, store = FakeRunner("x"), FakeStore()
    reply = HandleMessage(runner, store)(ANON, "   \n")
    assert reply.bubbles == (CHAT_ERROR,)
    assert runner.calls == []
    assert store.saved == []


def _runner(
    model: FakeToolCallingModel, saver: InMemorySaver | None = None
) -> tuple[GraphRunner, AgentGraph]:
    graph = build_graph(
        model, build_tools(make_box()), lambda _m: Scope.LOJA, saver or InMemorySaver()
    )
    return GraphRunner(graph, SETTINGS, RecordingTracer(), no_name), graph


def _usage(text: str, i: int, o: int) -> AIMessage:
    return AIMessage(
        text, usage_metadata={"input_tokens": i, "output_tokens": o, "total_tokens": i + o}
    )


def test_runner_sums_tokens_and_counts_calls_and_tools() -> None:
    call = AIMessage(
        content="",
        tool_calls=[{"name": "search_products", "args": {"query": "violao"}, "id": "c1"}],
        usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
    )
    model = FakeToolCallingModel(messages=iter([call, _usage("Temos.", 200, 20)]))
    runner, _ = _runner(model)
    text, scope, m = runner.run(ANON, "tem violão?")
    assert (text, scope) == ("Temos.", Scope.LOJA)
    assert (m.input_tokens, m.output_tokens, m.llm_calls) == (300, 30, 2)
    assert m.tools == ("search_products",)
    assert (m.trace_id, m.thread_id) == ("trace-1", "web:anon:s1")
    assert m.cost_brl is None  # Gemma is self-hosted: no per-token price
    assert m.ms_total >= m.ms_llm >= 0


def test_runner_prices_turn_with_settings_prices() -> None:
    cached = AIMessage(
        "Oi.",
        usage_metadata={
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "total_tokens": 2_000_000,
            "input_token_details": {"cache_read": 500_000},
        },
    )
    model = FakeToolCallingModel(messages=iter([cached]))
    graph = build_graph(model, build_tools(make_box()), lambda _m: Scope.LOJA, InMemorySaver())
    priced = Settings(_env_file=None, LLM_PROVIDER="openai")  # pyright: ignore[reportCallIssue]
    _, _, m = GraphRunner(graph, priced, RecordingTracer(), no_name).run(ANON, "oi")
    assert m.model == "gpt-6-luna"
    assert m.cached_tokens == 500_000
    usd = Decimal("0.10") * Decimal("0.5") + Decimal("0.01") * Decimal("0.5") + Decimal("0.50")
    assert m.cost_brl == usd * Decimal("5.50")


def _cost_runner(**env: str) -> GraphRunner:
    graph = build_graph(
        FakeToolCallingModel(messages=iter([])),
        build_tools(make_box()),
        lambda _m: Scope.LOJA,
        InMemorySaver(),
    )
    return GraphRunner(graph, Settings(_env_file=None, **env), RecordingTracer(), no_name)  # pyright: ignore[reportCallIssue]


def _timed_probe() -> TurnProbe:
    probe = TurnProbe()
    probe.ms_guard, probe.ms_llm = 0.4, 1.6
    return probe


def test_gemini_turn_is_priced() -> None:
    probe = _timed_probe()
    probe.input_tokens, probe.output_tokens = 1_000_000, 1_000_000
    runner = _cost_runner(LLM_PROVIDER="gemini", GEMINI_API_KEY="k")
    cost = runner._cost_brl("gemini-3.8-flash", probe)  # pyright: ignore[reportPrivateUsage]
    assert cost == (Decimal("0.75") + Decimal("3.75")) * Decimal("5.50")


def test_gemma_turn_cost_is_gpu_seconds_upper_bound() -> None:
    runner = _cost_runner(GPU_USD_PER_HOUR="3.95")
    cost = runner._cost_brl("google/gemma-4-31B-it", _timed_probe())  # pyright: ignore[reportPrivateUsage]
    assert cost == Decimal("3.95") * 2 / 3600 * Decimal("5.50")


def test_gemma_cost_null_without_gpu_price() -> None:
    runner = _cost_runner()
    assert runner._cost_brl("google/gemma-4-31B-it", _timed_probe()) is None  # pyright: ignore[reportPrivateUsage]


class _Exploding:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def invoke(self, *args: object, **kwargs: object) -> dict[str, object]:
        raise self.error


@pytest.mark.parametrize("error", [GraphRecursionError("loop"), RuntimeError("boom")])
def test_runner_turns_graph_failure_into_chat_error(error: Exception) -> None:
    graph: AgentGraph = _Exploding(error)  # pyright: ignore[reportAssignmentType]  # stub graph
    text, scope, m = GraphRunner(graph, SETTINGS, RecordingTracer(), no_name).run(ANON, "oi")
    assert (text, scope) == (CHAT_ERROR, Scope.LOJA)
    assert (m.trace_id, m.llm_calls) == ("trace-1", 0)
    assert m.ms_total >= 0


def test_new_customer_gets_fresh_thread() -> None:
    saver = InMemorySaver()
    model = FakeToolCallingModel(messages=iter([AIMessage("Oi, Ana."), AIMessage("Oi, Bia.")]))
    runner, graph = _runner(model, saver)
    runner.run(ChannelIdentity("web", 14, "s"), "meu pedido?")
    runner.run(ChannelIdentity("web", 3, "s"), "e o meu?")
    state = graph.get_state({"configurable": {"thread_id": "web:customer:3:s"}})
    texts = [m.text for m in state.values["messages"]]
    assert texts == ["e o meu?", "Oi, Bia."]
    assert all(isinstance(m, HumanMessage | AIMessage) for m in state.values["messages"])


class DbDown(Exception):
    pass


def test_empty_final_answer_becomes_chat_error() -> None:
    runner, _ = _runner(FakeToolCallingModel(messages=iter([AIMessage("")])))
    text, scope, _ = runner.run(ANON, "oi")
    assert (text, scope) == (CHAT_ERROR, Scope.LOJA)


def test_failing_name_lookup_returns_chat_error() -> None:
    def boom(_id: int) -> str | None:
        raise DbDown

    graph = build_graph(
        FakeToolCallingModel(messages=iter([AIMessage("x")])),
        build_tools(make_box()),
        lambda _m: Scope.LOJA,
        InMemorySaver(),
    )
    runner = GraphRunner(graph, SETTINGS, RecordingTracer(), boom)
    text, scope, m = runner.run(ChannelIdentity("web", 14, "s"), "oi")
    assert (text, scope, m.trace_id) == (CHAT_ERROR, Scope.LOJA, "trace-1")


def test_metrics_save_failure_keeps_the_reply() -> None:
    class Raising:
        def save(self, m: TurnMetrics) -> None:
            raise DbDown

    reply = HandleMessage(FakeRunner("Temos sim."), Raising())(ANON, "oi")
    assert reply.bubbles == ("Temos sim.",)


def test_guard_llm_time_is_not_counted_as_ms_llm() -> None:
    slow = FakeToolCallingModel(messages=iter([AIMessage("pronto")]))

    def slow_classify(_messages: object) -> Scope:
        time.sleep(0.05)  # stands in for the classifier's own model call
        slow.invoke("classifique")
        return Scope.LOJA

    model = FakeToolCallingModel(messages=iter([AIMessage("Oi.")]))
    graph = build_graph(model, build_tools(make_box()), slow_classify, InMemorySaver())
    runner = GraphRunner(graph, SETTINGS, RecordingTracer(), no_name)
    m = runner.run(ANON, "oi")[2]
    assert m.llm_calls == 2
    assert m.ms_guard >= 50
    assert m.ms_llm < m.ms_guard


def test_reply_carries_metrics() -> None:
    reply = HandleMessage(FakeRunner("Temos sim."), FakeStore())(ANON, "oi")
    assert reply.metrics == _metrics()
    assert reply.failed is False


def test_blank_message_is_failed() -> None:
    reply = HandleMessage(FakeRunner("x"), FakeStore())(ANON, " ")
    assert (reply.failed, reply.metrics) == (True, None)


class FakeRunnerOf:
    def __init__(self, metrics: TurnMetrics) -> None:
        self.metrics = metrics

    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]:
        return CHAT_ERROR, Scope.LOJA, self.metrics


def test_runner_failure_sets_failed() -> None:
    graph: AgentGraph = _Exploding(RuntimeError("boom"))  # pyright: ignore[reportAssignmentType]  # stub graph
    _, _, m = GraphRunner(graph, SETTINGS, RecordingTracer(), no_name).run(ANON, "oi")
    assert m.failed is True
    assert HandleMessage(FakeRunnerOf(m), FakeStore())(ANON, "oi").failed is True


def test_empty_answer_sets_failed() -> None:
    runner, _ = _runner(FakeToolCallingModel(messages=iter([AIMessage("")])))
    assert runner.run(ANON, "oi")[2].failed is True


def test_successful_turn_is_not_failed() -> None:
    runner, _ = _runner(FakeToolCallingModel(messages=iter([AIMessage("Oi.")])))
    assert runner.run(ANON, "oi")[2].failed is False
