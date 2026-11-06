from pathlib import Path

from fastapi.testclient import TestClient

from tests.fakes.fake_agent import FakeAgent
from tests.unit.api.conftest import (
    CREDENTIALS,
    PROXY_PHRASE,
    client_behind_proxy,
    client_with_multiplier,
    client_with_static,
)


def test_login_ok_sets_cookie_and_returns_warm_status(client: TestClient):
    response = client.post("/api/auth/login", json=CREDENTIALS)
    assert response.status_code == 200
    assert response.json()["warm"]["stage"] == "ready"
    cookie = response.headers["set-cookie"].lower()
    assert "emporio_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie


def test_wrong_password_401_and_no_cookie(client: TestClient):
    response = client.post("/api/auth/login", json={**CREDENTIALS, "password": "nope"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}
    assert "set-cookie" not in response.headers


def test_login_rejects_non_json_with_415(client: TestClient):
    response = client.post("/api/auth/login", data=CREDENTIALS)
    assert response.status_code == 415


def test_login_rate_limited_after_5_per_minute(client: TestClient):
    bad = {**CREDENTIALS, "password": "nope"}
    assert [client.post("/api/auth/login", json=bad).status_code for _ in range(5)] == [401] * 5
    assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 429


def test_login_limit_scales_with_multiplier(agent: FakeAgent):
    bad = {**CREDENTIALS, "password": "nope"}
    with client_with_multiplier(agent, 2) as client:
        codes = [client.post("/api/auth/login", json=bad).status_code for _ in range(11)]
    assert codes == [401] * 10 + [429]


def test_spoofed_client_ip_with_a_wrong_secret_is_still_limited(agent: FakeAgent):
    bad = {**CREDENTIALS, "password": "nope"}
    with client_behind_proxy(agent, PROXY_PHRASE) as client:
        codes = [
            client.post(
                "/api/auth/login",
                json=bad,
                headers={"X-Client-IP": f"198.51.100.{n}", "X-Proxy-Auth": "guess"},
            ).status_code
            for n in range(6)
        ]
    assert codes == [401] * 5 + [429]


def test_trusted_client_ips_are_limited_separately(agent: FakeAgent):
    bad = {**CREDENTIALS, "password": "nope"}
    with client_behind_proxy(agent, PROXY_PHRASE) as client:
        codes = [
            client.post(
                "/api/auth/login",
                json=bad,
                headers={"X-Client-IP": f"198.51.100.{n}", "X-Proxy-Auth": PROXY_PHRASE},
            ).status_code
            for n in range(6)
        ]
    assert codes == [401] * 6


def test_me_requires_session(client: TestClient):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_customer_and_warm_after_login(client: TestClient):
    client.post("/api/auth/login", json=CREDENTIALS)
    body = client.get("/api/auth/me").json()
    assert body["customer_id"] is None
    assert body["warm"]["stage"] == "ready"


def test_logout_clears_session(client: TestClient):
    client.post("/api/auth/login", json=CREDENTIALS)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_cookie_is_unauthenticated(client: TestClient):
    client.post("/api/auth/login", json=CREDENTIALS)
    value = client.cookies["emporio_session"]
    flipped = ("A" if value[0] != "A" else "B") + value[1:]
    client.cookies.clear()
    client.cookies.set("emporio_session", flipped)
    assert client.get("/api/auth/me").status_code == 401


def test_shutdown_closes_agent(agent: FakeAgent, client: TestClient):
    client.__exit__(None, None, None)
    assert agent.closed


def test_static_index_served_when_dist_exists(agent: FakeAgent, tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>oi</h1>")
    with client_with_static(agent, tmp_path) as client:
        assert "<h1>oi</h1>" in client.get("/").text
        assert client.get("/api/auth/me").status_code == 401


def test_missing_dist_does_not_crash(agent: FakeAgent, tmp_path: Path):
    with client_with_static(agent, tmp_path / "absent") as client:
        assert client.get("/").status_code == 404


def test_openapi_and_docs_are_not_served(agent: FakeAgent, tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>oi</h1>")
    with client_with_static(agent, tmp_path) as client:
        for path in ("/openapi.json", "/docs", "/redoc"):
            response = client.get(path)
            assert "openapi" not in response.text.lower()
            assert "swagger" not in response.text.lower()
