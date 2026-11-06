from datetime import date

import pytest

from emporio.config import ConfigError, Provider, Settings, load_settings

_ENV_VARS = (
    "LLM_PROVIDER", "VLLM_BASE_URL", "VLLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STORE_TODAY", "GEMMA_MODEL", "GEMINI_MODEL",
    "OPENAI_MODEL", "ANTHROPIC_MODEL",
)  # fmt: skip


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


def test_default_provider_is_gemma_and_needs_vllm_url(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(ConfigError, match="VLLM_BASE_URL"):
        load_settings()
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    assert load_settings().provider is Provider.GEMMA


@pytest.mark.parametrize(
    ("provider", "variable"),
    [
        (Provider.GEMINI, "GEMINI_API_KEY"),
        (Provider.OPENAI, "OPENAI_API_KEY"),
        (Provider.ANTHROPIC, "ANTHROPIC_API_KEY"),
    ],
)
def test_flag_without_key_raises_naming_variable(provider: Provider, variable: str):
    with pytest.raises(ConfigError, match=variable) as error:
        load_settings(provider)
    assert "gemma" in str(error.value)


def test_flag_with_key_loads(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    assert load_settings(Provider.OPENAI).provider is Provider.OPENAI


def test_store_today_defaults_to_2026_02_20():
    assert Settings().store_today == date(2026, 2, 20)
