import pytest
from fastapi.testclient import TestClient

from tests.fakes.fake_agent import FakeAgent
from tests.unit.api.conftest import CREDENTIALS


def login(client: TestClient) -> None:
    assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 200


def send(client: TestClient) -> None:
    client.post("/api/chat", json={"text": "oi"})


def test_customers_list_has_no_pii(client: TestClient, agent: FakeAgent) -> None:
    agent.known_customers = (14, 1, 2, 3, 4, 5, 6, 7)
    agent.demo_customers = FakeAgent(agent.known_customers).demo_customers
    login(client)
    body = client.get("/api/customers").json()
    assert len(body) == 8
    assert body[0]["id"] == 14
    assert all(set(item) == {"id", "name", "city"} for item in body)


def test_identity_switch_rotates_sid(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    send(client)
    response = client.put("/api/identity", json={"customer_id": 14})
    assert (response.status_code, response.json()) == (200, {"customer_id": 14})
    send(client)
    (first, _), (second, _) = agent.calls
    assert first.session != second.session
    assert (first.customer_id, second.customer_id) == (None, 14)


def test_unknown_customer_404_keeps_session(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    send(client)
    response = client.put("/api/identity", json={"customer_id": 999})
    assert (response.status_code, response.json()) == (404, {"detail": "unknown_customer"})
    send(client)
    assert agent.calls[0][0] == agent.calls[1][0]


def test_identity_null_clears_customer(client: TestClient, agent: FakeAgent) -> None:
    login(client)
    client.put("/api/identity", json={"customer_id": 14})
    send(client)
    assert client.put("/api/identity", json={"customer_id": None}).json() == {"customer_id": None}
    send(client)
    (before, _), (after, _) = agent.calls
    assert before.customer_id == 14
    assert after.customer_id is None
    assert before.session != after.session


def test_identity_requires_json(client: TestClient) -> None:
    login(client)
    assert (
        client.put("/api/identity", content="x", headers={"content-type": "text/plain"}).status_code
        == 415
    )


def test_identity_requires_session(client: TestClient) -> None:
    assert client.put("/api/identity", json={"customer_id": 14}).status_code == 401
    assert client.get("/api/customers").status_code == 401


def test_identity_rejects_non_int_and_out_of_range(
    client: TestClient, agent: FakeAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[int] = []
    monkeypatch.setattr(agent, "customer_exists", lambda customer_id: asked.append(customer_id))
    login(client)
    for bad in (True, 1.5, 1.0, 0, 2**40):
        assert client.put("/api/identity", json={"customer_id": bad}).status_code == 422
    assert asked == []
