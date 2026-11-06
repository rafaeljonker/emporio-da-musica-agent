from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from emporio.api.app import create_app
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ProbeWarmup
from tests.fakes.fake_agent import FakeAgent
from tests.unit.api.conftest import CREDENTIALS, make_settings

PROBES: list[int] = []


def _probe() -> bool:
    PROBES.append(1)
    return False


@pytest.fixture
def pending() -> ProbeWarmup:
    PROBES.clear()
    return ProbeWarmup(_probe, WarmMode.MODAL_GPU, 180, lambda: None, interval_seconds=0.01)


@pytest.fixture
def warm_client(pending: ProbeWarmup) -> Iterator[TestClient]:
    with TestClient(create_app(FakeAgent(), pending, make_settings())) as client:
        yield client


def test_warm_routes_require_session(warm_client: TestClient):
    assert warm_client.post("/api/warm").status_code == 401
    assert warm_client.get("/api/warm/status").status_code == 401


def test_warm_routes_return_status_with_session(warm_client: TestClient):
    warm_client.post("/api/auth/login", json=CREDENTIALS)
    started = warm_client.post("/api/warm")
    assert started.status_code == 200
    assert started.json()["stage"] == "server_starting"
    status = warm_client.get("/api/warm/status").json()
    assert (status["mode"], status["expected_seconds"]) == ("modal_gpu", 180)


def test_expected_is_public_and_starts_nothing(warm_client: TestClient, pending: ProbeWarmup):
    response = warm_client.get("/api/warm/expected")
    assert response.json() == {"mode": "modal_gpu", "expected_seconds": 180}
    pending.join(0.05)  # a started probe would have run by now
    assert PROBES == []
