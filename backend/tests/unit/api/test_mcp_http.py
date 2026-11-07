import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from emporio.api.app import create_app
from emporio.api.mcp_auth import current_mcp_customer
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.mcp.server import build_mcp_http_app
from emporio.support.infrastructure.warmup import ReadyWarmup
from tests.fakes.fake_agent import FakeAgent
from tests.fakes.fake_catalog_admin import FakeCatalogAdmin
from tests.unit.api.conftest import make_settings
from tests.unit.support.test_tools import make_box

ANON = "a" * 32
CUSTOMER_3 = "c" * 32
TOKENS = f"{ANON}=anon,{CUSTOMER_3}=3"
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
ACCEPT = "application/json, text/event-stream"


def _client(tokens: str, static_dir: Path | None = None) -> TestClient:
    app = create_app(
        FakeAgent(),
        ReadyWarmup(WarmMode.PROVIDER_API, lambda: None),
        make_settings(mcp_tokens=tokens),
        FakeCatalogAdmin(),
        static_dir=static_dir,
        mcp=build_mcp_http_app(make_box(), current_mcp_customer),
    )
    return TestClient(app)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with _client(TOKENS) as test_client:
        yield test_client


def _rpc(client: TestClient, body: dict[str, object], auth: str | None) -> Response:
    headers = {"accept": ACCEPT} | ({"authorization": auth} if auth is not None else {})
    return client.post("/mcp", json=body, headers=headers)


def _call(client: TestClient, token: str, tool: str) -> str:
    body = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool}}
    reply = _rpc(client, body, f"Bearer {token}")
    assert reply.status_code == 200, reply.text
    return reply.json()["result"]["content"][0]["text"]


def _assert_invalid_token(reply: Response) -> None:
    assert reply.status_code == 401
    assert reply.headers["www-authenticate"] == "Bearer"
    assert reply.json() == {"detail": "invalid_token"}


def test_missing_token_is_401(client: TestClient):
    _assert_invalid_token(_rpc(client, LIST_TOOLS, None))


def test_wrong_token_is_401(client: TestClient):
    _assert_invalid_token(_rpc(client, LIST_TOOLS, f"Bearer {'x' * 32}"))


def test_wrong_scheme_is_401(client: TestClient):
    _assert_invalid_token(_rpc(client, LIST_TOOLS, f"Basic {ANON}"))


def test_eleventh_failure_from_one_ip_is_429(client: TestClient):
    for _ in range(10):
        assert _rpc(client, LIST_TOOLS, "Bearer nope").status_code == 401
    assert _rpc(client, LIST_TOOLS, "Bearer nope").status_code == 429


def test_sixty_first_call_on_one_token_is_429(client: TestClient):
    for _ in range(60):
        assert _rpc(client, LIST_TOOLS, f"Bearer {ANON}").status_code == 200
    assert _rpc(client, LIST_TOOLS, f"Bearer {ANON}").status_code == 429
    assert _rpc(client, LIST_TOOLS, f"Bearer {CUSTOMER_3}").status_code == 200


def test_tools_list_has_the_ten_tools_without_customer_id(client: TestClient):
    reply = _rpc(client, LIST_TOOLS, f"Bearer {ANON}")

    listed = reply.json()["result"]["tools"]
    assert len(listed) == 10
    assert all("customer_id" not in json.dumps(t["inputSchema"]) for t in listed)


def test_each_token_sees_its_own_orders(client: TestClient):
    assert _call(client, ANON, "list_my_orders") == tools.ASK_ORDER_IDENTITY
    assert [o["id"] for o in json.loads(_call(client, CUSTOMER_3, "list_my_orders"))] == [2, 1]


def test_mcp_is_absent_without_tokens(tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>oi</h1>")
    with _client("", static_dir=tmp_path) as client:
        # The static mount answers: GET 404 (a POST gets its 405).
        assert client.get("/mcp", headers={"authorization": f"Bearer {ANON}"}).status_code == 404


def test_api_and_static_still_work_with_mcp_mounted(tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>oi</h1>")
    with _client(TOKENS, static_dir=tmp_path) as client:
        assert "<h1>oi</h1>" in client.get("/").text
        assert client.get("/api/auth/me").status_code == 401
        assert _rpc(client, LIST_TOOLS, f"Bearer {ANON}").status_code == 200
