import pytest

from emporio.config import Provider, Settings
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
        gemini_api_key="fake",
        openai_api_key="fake",
        anthropic_api_key="fake",
    )
    model = make_chat_model(settings)
    assert type(model).__name__ == class_name
    assert model_id in (getattr(model, "model_name", None), getattr(model, "model", None))
