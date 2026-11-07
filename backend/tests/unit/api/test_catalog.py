from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from emporio.api.app import create_app
from emporio.support.application.ports import ProductInput
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ReadyWarmup
from tests.fakes.fake_agent import FakeAgent
from tests.fakes.fake_catalog_admin import FakeCatalogAdmin
from tests.unit.api.conftest import CREDENTIALS, make_settings

BODY: dict[str, object] = {
    "name": "Cavaquinho Rozini RC-77X",
    "category_id": 5,
    "description": "Cavaquinho de choro",
    "price": "1234.5",
    "stock": 3,
    "status": "active",
    "specs": {"cordas": "aço"},
}


@pytest.fixture
def catalog() -> FakeCatalogAdmin:
    return FakeCatalogAdmin()


def _client(catalog: FakeCatalogAdmin) -> TestClient:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    return TestClient(create_app(FakeAgent(), warmup, make_settings(), catalog))


@pytest.fixture
def client(catalog: FakeCatalogAdmin) -> Iterator[TestClient]:
    with _client(catalog) as test_client:
        yield test_client


def login(client: TestClient) -> TestClient:
    assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 200
    return client


def test_catalog_routes_need_session(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    responses = [
        client.get("/api/catalog/categories"),
        client.get("/api/catalog/products/mine"),
        client.post("/api/catalog/products", json=BODY),
        client.put("/api/catalog/products/100000", json=BODY),
    ]
    assert [r.status_code for r in responses] == [401] * 4
    assert catalog.calls == []


def test_categories_lists_id_and_name(client: TestClient) -> None:
    login(client)
    response = client.get("/api/catalog/categories")
    assert (response.status_code, response.json()[0]) == (200, {"id": 5, "name": "Violões"})


def test_create_returns_201_with_decimal_string_price(
    client: TestClient, catalog: FakeCatalogAdmin
) -> None:
    login(client)
    response = client.post("/api/catalog/products", json=BODY)
    assert response.status_code == 201
    assert response.json() == {
        "id": 100000,
        "name": "Cavaquinho Rozini RC-77X",
        "category_id": 5,
        "category": "Violões",
        "description": "Cavaquinho de choro",
        "specs": {"cordas": "aço"},
        "price": "1234.50",
        "stock": 3,
        "status": "active",
    }
    [(action, owner, _, data)] = catalog.calls
    assert action == "create"
    assert owner  # the session's login id, never empty
    assert data == ProductInput(
        "Cavaquinho Rozini RC-77X",
        5,
        "Cavaquinho de choro",
        Decimal("1234.5"),
        3,
        "active",
        (("cordas", "aço"),),
    )
    assert data is not None
    assert isinstance(data.price, Decimal)


def _with(**changes: object) -> dict[str, object]:
    return {**BODY, **changes}


def _without(key: str) -> dict[str, object]:
    return {k: v for k, v in BODY.items() if k != key}


INVALID = {
    "extra_id": _with(id=1),
    "extra_source": _with(source="seed"),
    "extra_owner": _with(owner="someone"),
    "blank_name": _with(name="   "),
    "short_name": _with(name="a"),
    "long_name": _with(name="x" * 121),
    "missing_name": _without("name"),
    "price_exponent": _with(price="1e3"),
    "price_zero": _with(price="0"),
    "price_zero_cents": _with(price="0.00"),
    "price_three_decimals": _with(price="0.001"),
    "price_negative": _with(price="-5"),
    "price_too_big": _with(price="1234567"),
    "price_float": _with(price=12.5),
    "price_int": _with(price=12),
    "price_bool": _with(price=True),
    "stock_negative": _with(stock=-1),
    "stock_too_big": _with(stock=100001),
    "stock_string": _with(stock="3"),
    "stock_float": _with(stock=3.0),
    "category_string": _with(category_id="5"),
    "category_zero": _with(category_id=0),
    "category_bool": _with(category_id=True),
    "status_unknown": _with(status="deleted"),
    "description_too_long": _with(description="x" * 2001),
    "too_many_specs": _with(specs={f"k{i}": "v" for i in range(21)}),
    "spec_blank_key": _with(specs={" ": "v"}),
    "spec_blank_value": _with(specs={"k": "  "}),
    "spec_long_key": _with(specs={"k" * 41: "v"}),
    "spec_long_value": _with(specs={"k": "v" * 121}),
    "spec_number_value": _with(specs={"k": 1}),
    "name_nul": _with(name="Viol\x00ão"),
    "name_control": _with(name="Viol\x1bão"),
    "name_rtl": _with(name="Violão \u202eX"),
    "name_zero_width": _with(name="Viol\u200bão"),
    "name_isolate": _with(name="Violão \u2066X"),
    "spec_nul": _with(specs={"k": "v\x00"}),
    "spec_key_rtl": _with(specs={"k\u202e": "v"}),
    "description_nul": _with(description="a\x00b"),
    "description_rtl": _with(description="a\u202eb"),
}


@pytest.mark.parametrize("body", INVALID.values(), ids=INVALID.keys())
def test_create_rejects_invalid_bodies(
    client: TestClient, catalog: FakeCatalogAdmin, body: dict[str, object]
) -> None:
    login(client)
    assert client.post("/api/catalog/products", json=body).status_code == 422
    assert client.put("/api/catalog/products/100000", json=body).status_code == 422
    assert catalog.calls == []


def test_create_strips_whitespace(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    body = _with(name="  Cavaquinho  ", specs={" cordas ": " aço "})
    assert client.post("/api/catalog/products", json=body).status_code == 201
    data = catalog.calls[0][3]
    assert data is not None
    assert (data.name, data.specs) == ("Cavaquinho", (("cordas", "aço"),))


def test_create_requires_json(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    response = client.post(
        "/api/catalog/products", content=b"{}", headers={"content-type": "text/plain"}
    )
    assert (response.status_code, response.json()) == (415, {"detail": "json_required"})
    assert catalog.calls == []


def test_create_unknown_category_is_422(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    catalog.reject = "unknown_category"
    response = client.post("/api/catalog/products", json=_with(category_id=99))
    assert (response.status_code, response.json()) == (422, {"detail": "unknown_category"})


def test_put_foreign_or_seed_product_is_404(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    catalog.reject = "not_found"
    response = client.put("/api/catalog/products/95", json=BODY)
    assert (response.status_code, response.json()) == (404, {"detail": "not_found"})
    assert [(c[0], c[2]) for c in catalog.calls] == [("update", 95)]


def test_put_rejects_a_non_positive_id(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    assert client.put("/api/catalog/products/0", json=BODY).status_code == 422
    assert catalog.calls == []


def test_put_own_product_returns_200(client: TestClient) -> None:
    login(client)
    response = client.put("/api/catalog/products/100000", json=_with(price="99.9"))
    assert (response.status_code, response.json()["price"]) == (200, "99.90")


def test_catalog_full_is_409(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    catalog.reject = "catalog_full"
    response = client.post("/api/catalog/products", json=BODY)
    assert (response.status_code, response.json()) == (409, {"detail": "catalog_full"})


def test_eleventh_write_in_a_minute_is_429(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    statuses = [client.post("/api/catalog/products", json=BODY).status_code for _ in range(10)]
    # Rotating sid (a customer switch) must not reset a per-login window.
    assert client.put("/api/identity", json={"customer_id": 14}).status_code == 200
    response = client.put("/api/catalog/products/100000", json=BODY)
    assert statuses == [201] * 10
    assert (response.status_code, response.json()) == (429, {"detail": "too_many_writes"})
    assert len(catalog.calls) == 10


def test_mine_is_scoped_to_login(catalog: FakeCatalogAdmin) -> None:
    with _client(catalog) as first, _client(catalog) as second:
        login(first).post("/api/catalog/products", json=_with(name="Primeiro"))
        login(second).post("/api/catalog/products", json=_with(name="Segundo"))
        mine_first = first.get("/api/catalog/products/mine")
        assert first.put("/api/identity", json={"customer_id": 14}).status_code == 200
        still_first = first.get("/api/catalog/products/mine").json()
        mine_second = second.get("/api/catalog/products/mine").json()
    assert mine_first.status_code == 200
    assert [p["name"] for p in mine_first.json()] == ["Primeiro"]
    assert still_first == mine_first.json()  # the owner is the login, not the sid
    assert [p["name"] for p in mine_second] == ["Segundo"]
    owners = {owner for _, owner, _, _ in catalog.calls}
    assert len(owners) == 2


def test_description_keeps_line_breaks(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    body = _with(description="Tampo maciço.\nCordas de aço.")
    assert client.post("/api/catalog/products", json=body).status_code == 201
    data = catalog.calls[0][3]
    assert data is not None
    assert data.description == "Tampo maciço.\nCordas de aço."


def test_unavailable_catalog_is_503(client: TestClient, catalog: FakeCatalogAdmin) -> None:
    login(client)
    catalog.reject = "catalog_unavailable"
    created = client.post("/api/catalog/products", json=BODY)
    listed = client.get("/api/catalog/products/mine")
    assert (created.status_code, created.json()) == (503, {"detail": "catalog_unavailable"})
    assert (listed.status_code, listed.json()) == (503, {"detail": "catalog_unavailable"})


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def monotonic(self) -> float:
        return self.now


def test_new_logins_from_one_ip_share_the_write_limit(
    client: TestClient, catalog: FakeCatalogAdmin
) -> None:
    login(client)
    for _ in range(10):
        client.post("/api/catalog/products", json=BODY)
    client.post("/api/auth/logout")  # a fresh login gets a fresh lid, not a fresh IP window
    response = login(client).post("/api/catalog/products", json=BODY)
    assert (response.status_code, response.json()) == (429, {"detail": "too_many_writes"})
    assert len(catalog.calls) == 10


def test_thirty_first_create_in_an_hour_from_one_ip_is_429(
    client: TestClient, catalog: FakeCatalogAdmin, monkeypatch: pytest.MonkeyPatch
) -> None:
    from emporio.api import guards

    clock = FakeClock()
    monkeypatch.setattr(guards, "time", clock)
    statuses: list[int] = []
    for _ in range(31):
        clock.now += 61  # every per-minute window has emptied
        statuses.append(login(client).post("/api/catalog/products", json=BODY).status_code)
        client.post("/api/auth/logout")
    assert statuses == [201] * 30 + [429]
    clock.now += 61
    edit = login(client).put("/api/catalog/products/100000", json=BODY)
    assert edit.status_code == 200  # the hourly cap counts creates, not edits
