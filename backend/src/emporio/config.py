from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from emporio.paths import REPO_ROOT
from emporio.shared.errors import DomainError


class Provider(StrEnum):
    GEMMA = "gemma"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ConfigError(DomainError):
    """Startup configuration is missing or inconsistent."""


class InvalidSettings(ConfigError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Invalid configuration: {detail}")


class MissingSetting(ConfigError):
    def __init__(self, variable: str, provider: Provider, alternatives: str) -> None:
        super().__init__(
            f"{variable} is required for provider '{provider.value}'. "
            f"Set it, or choose another provider: {alternatives}."
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", extra="ignore", populate_by_name=True
    )

    provider: Provider = Field(default=Provider.GEMMA, validation_alias="LLM_PROVIDER")
    gemma_model: str = "google/gemma-4-31B-it"
    gemini_model: str = "gemini-3.8-flash"
    openai_model: str = "gpt-6-luna"
    anthropic_model: str = "claude-haiku-5-5"

    vllm_base_url: str | None = None
    vllm_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    database_url: str | None = None
    store_today: date = date(2026, 2, 20)

    # Optional until the tracing task makes them mandatory.
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str | None = None
    langfuse_salt: SecretStr | None = None

    usd_brl: Decimal = Decimal("5.50")
    # USD per million tokens (input, output, cached input). Empty for self-hosted Gemma.
    # Cached input is an estimate: 10% of the input price.
    prices: dict[str, tuple[Decimal, Decimal, Decimal]] = Field(
        default_factory=lambda: {
            "gpt-6-luna": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
            "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
        }
    )


_REQUIRED_VARIABLES = {
    Provider.GEMMA: ("VLLM_BASE_URL", "VLLM_API_KEY"),
    Provider.GEMINI: ("GEMINI_API_KEY",),
    Provider.OPENAI: ("OPENAI_API_KEY",),
    Provider.ANTHROPIC: ("ANTHROPIC_API_KEY",),
}


def _is_set(settings: Settings, variable: str) -> bool:
    value = getattr(settings, variable.lower())
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    return value is not None and bool(value.strip())


def require_provider_settings(settings: Settings) -> None:
    """Raise MissingSetting naming the first unset variable of the selected provider."""
    provider = settings.provider
    for variable in _REQUIRED_VARIABLES[provider]:
        if not _is_set(settings, variable):
            others = ", ".join(
                f"{p.value} ({' + '.join(_REQUIRED_VARIABLES[p])})"
                for p in Provider
                if p is not provider
            )
            raise MissingSetting(variable, provider, others)


def load_settings(provider: Provider | None = None) -> Settings:
    try:
        settings = Settings()
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        raise InvalidSettings(details) from error
    if provider is not None:
        settings = settings.model_copy(update={"provider": provider})
    require_provider_settings(settings)
    return settings
