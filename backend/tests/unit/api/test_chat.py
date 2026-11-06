import json
import threading
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from emporio.api.chat import action_label
from emporio.api.guards import ThreadLocks
from emporio.support.application.ports import Reply
from emporio.support.domain.scope import Scope
from tests.fakes.fake_agent import FakeAgent, turn_metrics
from tests.unit.api.conftest import CREDENTIALS

METRIC_KEYS = {
    "input_tokens", "output_tokens", "ms_model", "ms_guard", "ms_llm", "ms_tools",
    "cost_brl", "cost_basis", "action",
}  # fmt: skip


def login(client: TestClient) -> None:
    assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 200


def send(client: TestClient, text: str = "oi"):
    return client.post("/api/chat", json={"text": text})


def events(body: str) -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        out.append((fields["event"], json.loads(fields["data"])))
    return out


def two_bubbles(failed: bool = False, **kw: object) -> Reply:
    return Reply(
        ("Temos sim.", "Quer ver?"), Scope.LOJA, "trace-1", (),
        metrics=turn_metrics(**kw), failed=failed,  # pyright: ignore[reportArgumentType]
    )  # fmt: skip


def test_chat_event_order_and_payload_keys(client: TestClient, agent: FakeAgent) -> None:
    agent.reply = two_bubbles(tools=("search_products",), cost_brl=Decimal("0.01234"))
    login(client)
    response = send(client)
    assert response.headers["content-type"].startswith("text/event-stream")
    got = events(response.text)
    assert [name for name, _ in got] == ["typing", "bubble", "bubble", "metrics", "done"]
    assert got[0][1] == {}
    bubbles = [data for name, data in got if name == "bubble"]
    assert bubbles[0] == {"kind": "text", "text": "Temos sim.", "delay_ms": 0}
    assert bubbles[1]["delay_ms"] > 0  # pyright: ignore[reportIndexIssue,reportCallIssue,reportArgumentType]
    metrics = got[3][1]
    assert isinstance(metrics, dict)
    assert set(metrics) == METRIC_KEYS
    assert metrics["ms_model"] == 900
    assert metrics["cost_brl"] == "0.0123"
    assert metrics["cost_basis"] == "Estimado pelo preço de lista do provedor"
    assert got[4][1] == {"trace_id": "trace-1"}


@pytest.mark.parametrize(
    ("provider", "basis"),
    [
        ("gemma", "Custo de GPU ainda não medido"),
        ("gemini", "Preço do provedor ainda não confirmado"),
        ("fake", "Modo de teste, sem custo"),
    ],
)
def test_unpriced_metrics_basis_depends_on_provider(
    client: TestClient, agent: FakeAgent, provider: str, basis: str
) -> None:
    agent.reply = two_bubbles(provider=provider)
    login(client)
    metrics = events(send(client).text)[3][1]
    assert isinstance(metrics, dict)
    assert metrics["cost_brl"] is None
    assert metrics["cost_basis"] == basis
    assert metrics["action"] == "sem ferramenta"


def test_metrics_action_maps_tool_names() -> None:
    assert action_label(()) == "sem ferramenta"
    assert action_label(("search_products", "get_product")) == "busca no catálogo"
    assert (
        action_label(("calc_installments", "search_products", "store_now"))
        == "cálculo de parcelas + busca no catálogo + horário da loja"
    )
    assert action_label(("list_my_orders",)) == "consulta de pedido"
    assert action_label(("check_return_eligibility",)) == "consulta de troca"
    assert action_label(("search_policies",)) == "consulta às políticas"


def test_chat_uses_session_identity(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    send(client)
    identity, text = agent.calls[0]
    assert (identity.channel, identity.customer_id, text) == ("web", None, "oi")


def test_chat_rejects_customer_id_in_body(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    response = client.post("/api/chat", json={"text": "oi", "customer_id": 14})
    assert response.status_code == 422
    assert agent.calls == []


def test_chat_text_limits(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    assert send(client, "   ").status_code == 422
    assert send(client, "a" * 1001).status_code == 422
    assert agent.calls == []
    assert send(client, "a" * 1000).status_code == 200


def test_chat_requires_session_and_json(client: TestClient, agent: FakeAgent) -> None:
    assert send(client).status_code == 401
    login(client)
    assert client.post("/api/chat", content='{"text":"oi"}').status_code == 415
    assert agent.calls == []


def test_chat_rate_limited_per_session(client: TestClient) -> None:
    login(client)
    assert [send(client).status_code for _ in range(21)][-2:] == [200, 429]


def test_concurrent_turn_on_same_thread_gets_409(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    agent.block = threading.Event()
    first = threading.Thread(target=send, args=(client,))
    first.start()
    assert agent.entered.wait(5)
    second = send(client)
    assert (second.status_code, second.json()) == (409, {"detail": "turn_in_progress"})
    agent.block.set()
    first.join(5)
    assert send(client).status_code == 200


def test_stale_lock_is_reclaimed() -> None:
    now = [0.0]
    locks = ThreadLocks(stale_after=300, clock=lambda: now[0])
    first = locks.try_acquire("t")
    assert first is not None
    assert locks.try_acquire("t") is None
    now[0] = 301
    second = locks.try_acquire("t")
    assert second is not None
    locks.release("t", second)
    assert locks.try_acquire("t") is not None


def test_stale_owner_release_does_not_free_new_holder() -> None:
    now = [0.0]
    locks = ThreadLocks(stale_after=300, clock=lambda: now[0])
    old = locks.try_acquire("t")
    assert old is not None
    now[0] = 301
    new = locks.try_acquire("t")
    assert new is not None
    locks.release("t", old)
    assert locks.try_acquire("t") is None
    locks.release("t", new)
    assert locks.try_acquire("t") is not None


def test_failed_turn_emits_error_and_releases_lock(client: TestClient, agent: FakeAgent) -> None:
    agent.reply = two_bubbles(failed=True)
    login(client)
    assert events(send(client).text) == [("typing", {}), ("error", {"partial": False})]
    agent.reply = None
    assert events(send(client).text)[-1][0] == "done"


def test_exception_before_any_bubble_emits_error(client: TestClient, agent: FakeAgent) -> None:
    agent.error = RuntimeError("boom")
    login(client)
    assert events(send(client).text) == [("typing", {}), ("error", {"partial": False})]
    agent.error = None
    assert events(send(client).text)[-1][0] == "done"


def test_exception_after_a_bubble_emits_partial_error(
    client: TestClient, agent: FakeAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_m: object) -> dict[str, object]:
        raise RuntimeError("boom")

    agent.reply = two_bubbles()
    monkeypatch.setattr("emporio.api.chat._metrics_payload", boom)
    login(client)
    got = events(send(client).text)
    assert [name for name, _ in got] == ["typing", "bubble", "bubble", "error"]
    assert got[-1][1] == {"partial": True}
    monkeypatch.undo()
    assert events(send(client).text)[-1][0] == "done"


def test_identity_rotation_does_not_bypass_chat_limits(client: TestClient) -> None:
    login(client)
    codes = []
    for i in range(250):
        if i % 20 == 0:
            client.put("/api/identity", json={"customer_id": 14 if i % 40 else None})
        codes.append(send(client).status_code)
    assert 429 in codes
