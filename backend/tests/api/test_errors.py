"""One code-to-status map per error set, and a generic 500 that never echoes the error."""

import pytest
from fastapi.testclient import TestClient

from emporio.api.app import create_app
from emporio.api.errors import API_HTTP, CATALOG_HTTP, ApiErrorCode
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ReadyWarmup
from tests.api.helpers import make_settings
from tests.catalog.fakes import FakeCatalogAdmin
from tests.fakes.fake_agent import FakeAgent


def test_every_catalog_code_has_http_status() -> None:
    assert set(CATALOG_HTTP) == set(CatalogErrorCode)


def test_every_api_code_has_http_status() -> None:
    assert set(API_HTTP) == set(ApiErrorCode)


@pytest.mark.parametrize(
    ("code", "status", "detail"),
    [
        (CatalogErrorCode.UNKNOWN_CATEGORY, 422, "unknown_category"),
        (CatalogErrorCode.PRODUCT_NOT_OWNED, 404, "not_found"),
        (CatalogErrorCode.CATALOG_FULL, 409, "catalog_full"),
        (CatalogErrorCode.CATALOG_UNAVAILABLE, 503, "catalog_unavailable"),
        (CatalogErrorCode.NAME_TAKEN_BY_STORE, 422, "name_taken_by_store"),
        (CatalogErrorCode.PROMO_CLAIM, 422, "promo_claim"),
    ],
)
def test_catalog_wire_codes_unchanged(code: CatalogErrorCode, status: int, detail: str) -> None:
    assert (CATALOG_HTTP[code], code.value) == (status, detail)


def test_unexpected_error_returns_generic_500_without_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        FakeAgent(),
        ReadyWarmup(WarmMode.PROVIDER_API, lambda: None),
        make_settings(),
        FakeCatalogAdmin(),
    )

    def boom() -> None:
        raise RuntimeError("secret-xyz")

    app.add_api_route("/api/boom", boom)
    with (
        caplog.at_level("ERROR", logger="emporio.api"),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/api/boom")

    assert (response.status_code, response.json()) == (500, {"detail": "internal_error"})
    assert "secret-xyz" not in response.text
    assert "Traceback" not in response.text
    assert "secret-xyz" in caplog.text
