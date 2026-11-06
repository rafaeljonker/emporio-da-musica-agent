import pytest
from langchain_core.messages import AIMessage
from langfuse import Langfuse
from langfuse.types import MaskOtelSpansParams, OtelSpanData, OtelSpanIdentifier
from langgraph.checkpoint.memory import InMemorySaver

from emporio.config import ConfigError, Settings
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.runner import GraphRunner
from emporio.support.infrastructure.agent.tools import build_tools
from emporio.support.infrastructure.tracing import (
    LangfuseTracerFactory,
    make_langfuse,
    mask_otel_spans,
    pseudonym,
)
from tests.fakes.fake_chat_model import FakeToolCallingModel
from tests.fakes.recording_tracer import RecordingTracer
from tests.unit.support.test_tools import make_box

FAKE_SK = "sk"


def _offline_client() -> Langfuse:
    return Langfuse(
        public_key="pk", secret_key=FAKE_SK, base_url="http://x.test", tracing_enabled=False
    )


def test_pseudonym_is_stable_and_not_the_id() -> None:
    first = pseudonym("salt", 42)
    assert first == pseudonym("salt", 42)
    assert first != pseudonym("other-salt", 42)
    assert first.startswith("cust-")
    assert len(first) == len("cust-") + 10
    assert pseudonym("salt", None) == "anon"


def test_turn_metadata_sets_session_and_pseudonymous_user() -> None:
    client = _offline_client()
    factory = LangfuseTracerFactory(client, "salt")
    meta = factory.turn_metadata(ChannelIdentity("web", 7, "s"))
    assert meta == {
        "langfuse_session_id": "web:customer:7",
        "langfuse_user_id": pseudonym("salt", 7),
    }


def test_for_turn_returns_fresh_handler_and_distinct_trace_ids() -> None:
    client = _offline_client()
    factory = LangfuseTracerFactory(client, "salt")
    who = ChannelIdentity("web", None, "s")
    (a,), id_a = factory.for_turn(who)
    (b,), id_b = factory.for_turn(who)
    assert a is not b
    assert id_a != id_b
    assert len(id_a) == 32


def test_mask_redacts_email_phone_cpf() -> None:
    text = (
        "joao@exemplo.com.br (67) 98432-1098 67984321098 +55 67 98432-1098 "
        "000.000.000-00 12345678901 pedido 1042"
    )
    key = OtelSpanIdentifier("a" * 32, "b" * 16)
    span = OtelSpanData("a" * 32, "b" * 16, None, "n", None, None, {"input": text, "n": 3}, {})
    result = mask_otel_spans(params=MaskOtelSpansParams(spans={key: span}))
    patch = result.span_patches[key]
    assert patch is not None
    masked = str(patch.set_attributes["input"])
    assert masked == "[REDACTED] [REDACTED] [REDACTED] [REDACTED] [REDACTED] [REDACTED] pedido 1042"
    assert "n" not in patch.set_attributes


def test_make_langfuse_without_settings_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="make langfuse-up"):
        make_langfuse(Settings(_env_file=None))  # pyright: ignore[reportCallIssue]


def test_fake_tracer_records_one_trace_per_turn() -> None:
    model = FakeToolCallingModel(messages=iter([AIMessage("Oi."), AIMessage("Tchau.")]))
    graph = build_graph(model, build_tools(make_box()), lambda _m: Scope.LOJA, InMemorySaver())
    tracer = RecordingTracer()
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    runner = GraphRunner(graph, settings, tracer, lambda _id: None)
    who = ChannelIdentity("web", None, "s1")
    first = runner.run(who, "oi")[2]
    second = runner.run(who, "tchau")[2]
    assert [first.trace_id, second.trace_id] == ["trace-1", "trace-2"]
    assert tracer.turns == [who, who]
