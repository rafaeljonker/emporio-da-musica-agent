from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from emporio.config import Provider, Settings, require_provider_settings

_TEMPERATURE = 0.3


def make_chat_model(settings: Settings) -> BaseChatModel:
    """Build the chat model for the configured provider; no network call happens here."""
    require_provider_settings(settings)
    match settings.provider:
        case Provider.GEMMA:
            return init_chat_model(
                settings.gemma_model,
                model_provider="openai",
                base_url=settings.vllm_base_url,
                api_key=settings.vllm_api_key,
                temperature=_TEMPERATURE,
            )
        case Provider.GEMINI:
            return init_chat_model(
                settings.gemini_model,
                model_provider="google_genai",
                api_key=settings.gemini_api_key,
                thinking_level="low",  # 3.8 Flash rejects "minimal" (400)
                temperature=_TEMPERATURE,
            )
        case Provider.OPENAI:
            return init_chat_model(
                settings.openai_model,
                model_provider="openai",
                api_key=settings.openai_api_key,
                temperature=_TEMPERATURE,
            )
        case Provider.LOCAL:
            # Ollama ignores the key but the OpenAI client needs a non-empty one.
            return init_chat_model(
                settings.ollama_model,
                model_provider="openai",
                base_url=settings.ollama_base_url,
                api_key="ollama",
                temperature=_TEMPERATURE,
            )
        case Provider.ANTHROPIC:
            return init_chat_model(
                settings.anthropic_model,
                model_provider="anthropic",
                api_key=settings.anthropic_api_key,
                temperature=_TEMPERATURE,
            )


def make_guard_model(settings: Settings) -> BaseChatModel:
    """Model for the scope classifier: Gemini uses a Flash-Lite model, others the chat model."""
    if settings.provider is not Provider.GEMINI:
        return make_chat_model(settings)
    require_provider_settings(settings)
    return init_chat_model(
        settings.gemini_guard_model,
        model_provider="google_genai",
        api_key=settings.gemini_api_key,
        thinking_level="minimal",  # Flash-Lite accepts "minimal" (3.8 Flash does not)
        temperature=_TEMPERATURE,
    )
