from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from emporio.api.app import create_app
from emporio.platform.config import Settings
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ReadyWarmup
from tests.fakes.fake_agent import FakeAgent
from tests.fakes.fake_catalog_admin import FakeCatalogAdmin

EMAIL = "demo@emporio.test"
LOGIN_PHRASE = "correct-horse"
CREDENTIALS = {"email": EMAIL, "password": LOGIN_PHRASE}
PROXY_PHRASE = "shh"


def make_settings(
    rate_limit_multiplier: int = 1, proxy_secret: str | None = None, mcp_tokens: str = ""
) -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]  # pydantic-settings init kwarg
        demo_email=EMAIL,
        demo_password=SecretStr(LOGIN_PHRASE),
        session_secret=SecretStr("s" * 40),
        session_https_only=False,
        fake_model=True,
        rate_limit_multiplier=rate_limit_multiplier,
        proxy_secret=SecretStr(proxy_secret) if proxy_secret else None,
        mcp_tokens=SecretStr(mcp_tokens),
    )


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def client(agent: FakeAgent) -> Iterator[TestClient]:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    with TestClient(create_app(agent, warmup, make_settings(), FakeCatalogAdmin())) as test_client:
        yield test_client


def client_with_multiplier(agent: FakeAgent, multiplier: int) -> TestClient:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    return TestClient(create_app(agent, warmup, make_settings(multiplier), FakeCatalogAdmin()))


def client_with_static(agent: FakeAgent, static_dir: Path) -> TestClient:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    return TestClient(
        create_app(agent, warmup, make_settings(), FakeCatalogAdmin(), static_dir=static_dir)
    )


def client_behind_proxy(agent: FakeAgent, proxy_secret: str) -> TestClient:
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    return TestClient(
        create_app(agent, warmup, make_settings(proxy_secret=proxy_secret), FakeCatalogAdmin())
    )
