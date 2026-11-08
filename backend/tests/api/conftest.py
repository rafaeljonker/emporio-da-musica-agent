from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from emporio.api.app import create_app
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ReadyWarmup
from tests.api.helpers import make_settings
from tests.catalog.fakes import FakeCatalogAdmin
from tests.fakes.fake_agent import FakeAgent


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def client(agent: FakeAgent) -> Iterator[TestClient]:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    with TestClient(create_app(agent, warmup, make_settings(), FakeCatalogAdmin())) as test_client:
        yield test_client
