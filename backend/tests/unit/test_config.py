from datetime import date

import pytest

from emporio.config import ConfigError, Provider, Settings, load_mcp_settings, load_settings

_ENV_VARS = (
    "LLM_PROVIDER", "VLLM_BASE_URL", "VLLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STORE_TODAY", "GEMMA_MODEL", "GEMINI_MODEL",
    "OPENAI_MODEL", "ANTHROPIC_MODEL", "USD_BRL", "DATABASE_URL", "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "LANGFUSE_SALT", "LANGFUSE_TRACING_ENABLED",
    "OTEL_SDK_DISABLED", "LANGFUSE_SAMPLE_RATE",
)  # fmt: skip
_FAKE_LANGFUSE = {
    "LANGFUSE_PUBLIC_KEY": "pk-fake",
    "LANGFUSE_SECRET_KEY": "sk-fake",
    "LANGFUSE_BASE_URL": "http://langfuse.test",
    "LANGFUSE_SALT": "salt-fake",
}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in _FAKE_LANGFUSE.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


def test_default_provider_is_gemma_and_needs_vllm_url(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(ConfigError, match="VLLM_BASE_URL"):
        load_settings()
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    monkeypatch.setenv("VLLM_API_KEY", "fake")
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


def test_gemma_without_vllm_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    with pytest.raises(ConfigError, match="VLLM_API_KEY"):
        load_settings()


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch, blank: str):
    monkeypatch.setenv("GEMINI_API_KEY", blank)
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_settings(Provider.GEMINI)


def test_invalid_value_error_never_echoes_the_input(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("USD_BRL", "super-secret-garbage")
    with pytest.raises(ConfigError, match="usd_brl") as error:
        load_settings()
    assert "super-secret-garbage" not in str(error.value)


def test_missing_langfuse_vars_fail_startup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    for name in _FAKE_LANGFUSE:
        monkeypatch.delenv(name)
    with pytest.raises(ConfigError, match="make langfuse-up") as error:
        load_settings(Provider.OPENAI)
    for name in _FAKE_LANGFUSE:
        assert name in str(error.value)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("LANGFUSE_TRACING_ENABLED", "false"),
        ("OTEL_SDK_DISABLED", "true"),
        ("LANGFUSE_SAMPLE_RATE", "0.5"),
        ("LANGFUSE_SAMPLE_RATE", "nan"),
        ("LANGFUSE_SAMPLE_RATE", "2"),
    ],
)
def test_disabling_vars_are_rejected(monkeypatch: pytest.MonkeyPatch, variable: str, value: str):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv(variable, value)
    with pytest.raises(ConfigError, match=variable):
        load_settings(Provider.OPENAI)


def test_mcp_settings_load_without_provider_vars():
    assert load_mcp_settings().provider is Provider.GEMMA
    with pytest.raises(ConfigError, match="VLLM_BASE_URL"):
        load_settings()
