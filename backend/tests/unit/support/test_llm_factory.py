import pytest
from pydantic import SecretStr

from emporio.config import ConfigError, Provider, Settings
from emporio.support.infrastructure.llm.factory import make_chat_model


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


@pytest.mark.parametrize(
    ("provider", "class_name", "model_id"),
    [
        (Provider.GEMMA, "ChatOpenAI", "google/gemma-4-31B-it"),
        (Provider.GEMINI, "ChatGoogleGenerativeAI", "gemini-3.8-flash"),
        (Provider.OPENAI, "ChatOpenAI", "gpt-6-luna"),
        (Provider.ANTHROPIC, "ChatAnthropic", "claude-haiku-5-5"),
    ],
)
def test_factory_builds_each_provider_without_network(
    provider: Provider, class_name: str, model_id: str
):
    settings = Settings(
        provider=provider,
        vllm_base_url="http://vllm.test/v1",
        vllm_api_key=SecretStr("fake"),
        gemini_api_key=SecretStr("fake"),
        openai_api_key=SecretStr("fake"),
        anthropic_api_key=SecretStr("fake"),
    )
    model = make_chat_model(settings)
    assert type(model).__name__ == class_name
    assert getattr(model, "temperature", None) == 0.3
    assert model_id in (getattr(model, "model_name", None), getattr(model, "model", None))


def test_gemini_thinking_is_minimal():
    model = make_chat_model(Settings(provider=Provider.GEMINI, gemini_api_key=SecretStr("fake")))
    assert getattr(model, "thinking_level", None) == "minimal"


def test_gemma_without_base_url_raises():
    with pytest.raises(ConfigError, match="VLLM_BASE_URL"):
        make_chat_model(Settings(provider=Provider.GEMMA))


def test_local_provider_uses_the_ollama_openai_endpoint():
    model = make_chat_model(Settings(provider=Provider.LOCAL))
    assert type(model).__name__ == "ChatOpenAI"
    assert getattr(model, "model_name", None) == "emporio-gemma"
    assert str(getattr(model, "openai_api_base", "")) == "http://localhost:11434/v1"
