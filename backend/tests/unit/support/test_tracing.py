import logging
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langfuse import Langfuse
from langfuse.types import MaskOtelSpansParams, OtelSpanData, OtelSpanIdentifier
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from emporio.config import ConfigError, Settings
from emporio.orders.domain.identity import normalize_phone
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.runner import GraphRunner
from emporio.support.infrastructure.agent.tools import build_tools
from emporio.support.infrastructure.tracing import (
    REDACTED,
    LangfuseTracerFactory,
    make_langfuse,
    mask_otel_spans,
    pseudonym,
    redact,
)
from tests.fakes.fake_chat_model import FakeToolCallingModel
from tests.fakes.recording_tracer import RecordingTracer
from tests.unit.support.test_tools import make_box

FAKE_SK = "sk"


def _offline_client() -> Langfuse:
    return Langfuse(
        public_key="pk", secret_key=FAKE_SK, base_url="http://x.test", tracing_enabled=False
    )


def _all_digit_customer(salt: str) -> int:
    return next(i for i in range(10_000) if pseudonym(salt, i).removeprefix("cust-").isdigit())


def test_pseudonym_survives_redact() -> None:
    who = pseudonym("salt", _all_digit_customer("salt"))
    assert redact(f"user {who} asked") == f"user {who} asked"
    digits = who.removeprefix("cust-")
    key = OtelSpanIdentifier("a" * 32, "b" * 16)
    attributes = {"user.id": digits, "session.id": digits, "langfuse.user.id": digits}
    span = OtelSpanData("a" * 32, "b" * 16, None, "n", None, None, attributes, {})
    assert mask_otel_spans(params=MaskOtelSpansParams(spans={key: span})).span_patches == {}


def test_hex_id_not_redacted() -> None:
    ids = "trace 12345678901234567890123456789012 span 1234567890123456 cust-1234567890"
    assert redact(ids) == ids


def test_handler_is_bound_to_our_client() -> None:
    other = Langfuse(
        public_key="pk-other", secret_key=FAKE_SK, base_url="http://y.test", tracing_enabled=False
    )
    ours = _offline_client()
    (handler,), _ = LangfuseTracerFactory(ours, "salt", "pk").for_turn(
        ChannelIdentity("web", None, "s")
    )
    bound = vars(handler)["_langfuse_client"]
    assert bound._resources is ours._resources  # pyright: ignore[reportPrivateUsage]
    assert bound._resources is not other._resources  # pyright: ignore[reportPrivateUsage]


def test_pseudonym_is_stable_and_not_the_id() -> None:
    first = pseudonym("salt", 42)
    assert first == pseudonym("salt", 42)
    assert first != pseudonym("other-salt", 42)
    assert first.startswith("cust-")
    assert len(first) == len("cust-") + 10
    assert pseudonym("salt", None) == "anon"


def test_turn_metadata_sets_session_and_pseudonymous_user() -> None:
    client = _offline_client()
    factory = LangfuseTracerFactory(client, "salt", "pk")
    meta = factory.turn_metadata(ChannelIdentity("web", 7, "s"))
    assert meta == {
        "langfuse_session_id": f"web:{pseudonym('salt', 7)}:s",
        "langfuse_user_id": pseudonym("salt", 7),
        "thread_id": f"web:{pseudonym('salt', 7)}:s",
    }
    assert ":customer:" not in meta["langfuse_session_id"]


def test_langfuse_session_scoped_and_pseudonymous() -> None:
    factory = LangfuseTracerFactory(_offline_client(), "salt", "pk")
    session = factory.turn_metadata(ChannelIdentity("web", 14, "abc"))["langfuse_session_id"]
    assert session == f"web:{pseudonym('salt', 14)}:abc"
    assert ":customer:" not in session


def test_anonymous_session_id_keeps_the_anon_thread_shape() -> None:
    factory = LangfuseTracerFactory(_offline_client(), "salt", "pk")
    meta = factory.turn_metadata(ChannelIdentity("web", None, "s"))
    assert meta["langfuse_session_id"] == "web:anon:s"


def test_for_turn_returns_fresh_handler_and_distinct_trace_ids() -> None:
    client = _offline_client()
    factory = LangfuseTracerFactory(client, "salt", "pk")
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


def test_failed_auth_check_shuts_the_client_down(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from emporio.config import LangfuseUnreachable, Settings
    from emporio.support.infrastructure import tracing

    shut: list[bool] = []
    fake = SimpleNamespace(auth_check=lambda: False, shutdown=lambda: shut.append(True))
    monkeypatch.setattr(tracing, "Langfuse", lambda **kwargs: fake)
    monkeypatch.setattr(tracing, "require_langfuse_settings", lambda s: None)
    with pytest.raises(LangfuseUnreachable):
        tracing.make_langfuse(Settings())
    assert shut == [True]


def _exported_runner(
    replies: list[AIMessage], customer_name: str | None = None
) -> tuple[GraphRunner, InMemorySpanExporter, Langfuse, LangfuseTracerFactory]:
    exporter = InMemorySpanExporter()
    key = f"pk-export-{uuid4().hex}"  # the SDK keeps one client per public key
    client = Langfuse(
        public_key=key,
        secret_key=FAKE_SK,
        base_url="http://x.test",
        tracing_enabled=True,
        sample_rate=1.0,
        mask_otel_spans=mask_otel_spans,
        span_exporter=exporter,
    )
    tracer = LangfuseTracerFactory(client, "salt", key)
    model = FakeToolCallingModel(messages=iter(replies))
    graph = build_graph(model, build_tools(make_box()), lambda _m: Scope.LOJA, InMemorySaver())
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    return GraphRunner(graph, settings, tracer, lambda _id: customer_name), exporter, client, tracer


def _exported_text(exporter: InMemorySpanExporter) -> str:
    lines: list[str] = []
    for span in exporter.get_finished_spans():
        lines += [f"{k}={v}" for k, v in (span.attributes or {}).items()]
        lines.append(span.status.description or "")
        lines += [str(e.attributes) for e in span.events]
    return "\n".join(lines)


def test_exported_spans_never_carry_the_raw_thread_id() -> None:
    runner, exporter, client, _ = _exported_runner([AIMessage("Oi.")])
    runner.run(ChannelIdentity("web", 3, "s"), "oi")
    client.flush()
    exported = _exported_text(exporter)
    assert exported
    assert "customer:3" not in exported
    assert f"session.id=web:{pseudonym('salt', 3)}" in exported


@pytest.mark.parametrize(
    "args",
    [
        {"order_id": "cinco", "email_or_phone": "outra@jmail.com"},
        {"order_id": 5, "email_or_phone": ["outra@jmail.com"]},
        {"order_id": 5, "email_or_phone": 67984321098},
    ],
)
def test_malformed_tool_args_leak_nothing_to_logs_or_spans(
    args: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    call = AIMessage("", tool_calls=[{"name": "get_order_status", "args": args, "id": "c1"}])
    runner, exporter, client, _ = _exported_runner([call, AIMessage("ok")])
    with caplog.at_level(logging.DEBUG):
        answer = runner.run(ChannelIdentity("web", None, "s"), "pedido 5")[0]
    client.flush()
    assert answer == "ok"
    exported = _exported_text(exporter)
    assert "get_order_status" in exported
    for secret in ("outra@jmail", "67984321098", "jmail"):
        assert secret not in exported
        assert secret not in caplog.text


@pytest.mark.parametrize(
    "phone",
    [
        "67 9 8432 1098",
        "(67) 9 8432-1098",
        "55 67 9 8432-1098",
        "+55 (67) 9 8432 1098",
        "67.98432.1098",
        "679 843 210 98",
        "67 3321 4455",
        "(67)3321-4455",
        "5567984321098",
    ],
)
def test_phone_with_any_separators_is_redacted(phone: str) -> None:
    # Each of these authenticates as the same phone, so each must be masked.
    assert len(normalize_phone(phone)) in (10, 11)
    assert redact(f"meu telefone: {phone}, ok") == f"meu telefone: {REDACTED}, ok"


@pytest.mark.parametrize(
    "text",
    [
        "pedido 1042 e 2026",
        "das 9h-18h",
        "12/11/2026 as 14:30",
        "R$ 2.199,00 em 12x",
        "cust-1234567890",
        "span 1234567890123456 hex 12345678901234567890123456789012",
        "1 2 3 4",
    ],
)
def test_identifiers_and_plain_numbers_are_not_redacted(text: str) -> None:
    assert redact(text) == text
