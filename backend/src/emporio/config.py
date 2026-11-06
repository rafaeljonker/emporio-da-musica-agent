from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from emporio.paths import REPO_ROOT
from emporio.shared.errors import DomainError
from emporio.support.application.warmup import WarmMode


class Provider(StrEnum):
    GEMMA = "gemma"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ConfigError(DomainError):
    """Startup configuration is missing or inconsistent."""


class InvalidSettings(ConfigError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Invalid configuration: {detail}")


class UnknownCustomer(ConfigError):
    def __init__(self, customer_id: int) -> None:
        super().__init__(f"cliente {customer_id} não encontrado")


class MissingSetting(ConfigError):
    def __init__(self, variable: str, provider: Provider, alternatives: str) -> None:
        super().__init__(
            f"{variable} is required for provider '{provider.value}'. "
            f"Set it, or choose another provider: {alternatives}."
        )


class LangfuseRequired(ConfigError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__(
            f"Langfuse tracing is mandatory: {'; '.join(problems)}. "
            "Run `make langfuse-up` to start a local Langfuse and write its keys to .env. "
            "On deploy, the keys live in the Modal secret `emporio-langfuse`."
        )


class LangfuseUnreachable(ConfigError):
    def __init__(self, base_url: str | None) -> None:
        super().__init__(
            f"Langfuse auth_check failed against {base_url}: wrong keys or the server is down. "
            "Run `make langfuse-up` for a local Langfuse."
        )


class WebSettingsRequired(ConfigError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__(f"Web settings are required: {'; '.join(problems)}.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", extra="ignore", populate_by_name=True
    )

    provider: Provider = Field(default=Provider.GEMMA, validation_alias="LLM_PROVIDER")
    # Scripted model and classifier for e2e and dev: no provider key, Langfuse still mandatory.
    fake_model: bool = Field(default=False, validation_alias="EMPORIO_FAKE_MODEL")
    gemma_model: str = "google/gemma-4-31B-it"
    gemini_model: str = "gemini-3.8-flash"
    # Scope classifier only: a Flash-Lite model cuts the guard from ~2.7 s to ~0.9 s.
    gemini_guard_model: str = "gemini-3.1-flash-lite"
    openai_model: str = "gpt-6-luna"
    anthropic_model: str = "claude-haiku-5-5"
    # Ollama on this machine; `emporio local-model` creates the model with a 16k context.
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "emporio-gemma"

    vllm_base_url: str | None = None
    vllm_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    database_url: str | None = None
    # Read pool per process; the load-test app raises it to measure the API, not the pool.
    db_pool_max: int = Field(default=4, ge=1)
    store_today: date = date(2026, 2, 20)

    # Mandatory tracing: presence and the three disabling switches are enforced in load_settings.
    langfuse_tracing_enabled: bool = True
    otel_sdk_disabled: bool = False
    langfuse_sample_rate: float = 1.0
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str | None = None
    langfuse_salt: SecretStr | None = None

    warm_expected_seconds_gpu: int = 180  # measured 175 s; phase 6 re-measures
    warm_expected_seconds_local: int = 120
    # A READY older than this is probed again on login/warm (phase 6: Modal's scaledown window).
    warm_ready_ttl_seconds: int = 300
    # Fake warm-up for e2e: the model "becomes ready" after N seconds (0 = ready at once).
    fake_warm_seconds: int = Field(default=0, validation_alias="EMPORIO_FAKE_WARM_SECONDS")
    fake_warm_mode: WarmMode = Field(
        default=WarmMode.MODAL_GPU, validation_alias="EMPORIO_FAKE_WARM_MODE"
    )

    demo_email: str | None = None
    demo_password: SecretStr | None = None
    session_secret: SecretStr | None = None
    session_https_only: bool = True
    session_max_age_seconds: int = 28800
    # Scales the login and chat rate limits for load tests; only with the fake model (no GPU cost).
    rate_limit_multiplier: int = Field(default=1, ge=1)

    @property
    def provider_name(self) -> str:
        """What metrics and reports call the provider: "fake" under the scripted model."""
        return "fake" if self.fake_model else self.provider.value

    usd_brl: Decimal = Decimal("5.50")
    # GPU rental in USD per hour: prices Gemma turns as an upper bound (concurrency 1).
    gpu_usd_per_hour: Decimal | None = None
    # USD per million tokens (input, output, cached input). Gemma is priced by GPU time instead.
    # Cached input is an estimate: 10% of the input price.
    prices: dict[str, tuple[Decimal, Decimal, Decimal]] = Field(
        default_factory=lambda: {
            # list price until 2026-12-31; 1.50 / 7.50 / 0.15 from 2027-01-01
            "gemini-3.8-flash": (Decimal("0.75"), Decimal("3.75"), Decimal("0.075")),
            "gemini-3.1-flash-lite": (Decimal("0.25"), Decimal("1.50"), Decimal("0.025")),
            "gpt-6-luna": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
            "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
        }
    )


_REQUIRED_VARIABLES = {
    Provider.GEMMA: ("VLLM_BASE_URL", "VLLM_API_KEY"),
    Provider.GEMINI: ("GEMINI_API_KEY",),
    Provider.OPENAI: ("OPENAI_API_KEY",),
    Provider.ANTHROPIC: ("ANTHROPIC_API_KEY",),
    Provider.LOCAL: (),
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
                f"{p.value} ({' + '.join(_REQUIRED_VARIABLES[p]) or 'no key'})"
                for p in Provider
                if p is not provider
            )
            raise MissingSetting(variable, provider, others)


_LANGFUSE_REQUIRED = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_SALT",
)


def require_langfuse_settings(settings: Settings) -> None:
    """Tracing is mandatory: raise naming every missing or tracing-disabling variable."""
    problems = [f"{v} is not set" for v in _LANGFUSE_REQUIRED if not _is_set(settings, v)]
    if not settings.langfuse_tracing_enabled:
        problems.append("LANGFUSE_TRACING_ENABLED must not be false")
    if settings.otel_sdk_disabled:
        problems.append("OTEL_SDK_DISABLED must not be true")
    if settings.langfuse_sample_rate != 1:
        problems.append("LANGFUSE_SAMPLE_RATE must be 1 (no sampling)")
    if problems:
        raise LangfuseRequired(problems)


def _read_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        raise InvalidSettings(details) from error


def load_mcp_settings() -> Settings:
    """Settings for the MCP server: no model and no tracing, so no provider/Langfuse checks."""
    return _read_settings()


def load_provider_settings(provider: Provider | None = None) -> Settings:
    """Settings with the provider check only: a fast fail before slow setup (Docker, Langfuse)."""
    settings = _read_settings()
    if provider is not None:
        settings = settings.model_copy(update={"provider": provider})
    if not settings.fake_model:
        require_provider_settings(settings)
    return settings


def load_settings(provider: Provider | None = None) -> Settings:
    settings = load_provider_settings(provider)
    require_langfuse_settings(settings)
    return settings


_MIN_SESSION_SECRET = 32


def require_web_settings(settings: Settings) -> None:
    """Raise naming every missing demo-login variable and a too-short SESSION_SECRET."""
    problems = [
        f"{v} is not set" for v in ("DEMO_EMAIL", "DEMO_PASSWORD") if not _is_set(settings, v)
    ]
    if not _is_set(settings, "SESSION_SECRET"):
        problems.append("SESSION_SECRET is not set (`make web-keys` writes one)")
    elif len(_secret_text(settings.session_secret)) < _MIN_SESSION_SECRET:
        problems.append(f"SESSION_SECRET must have at least {_MIN_SESSION_SECRET} characters")
    if settings.rate_limit_multiplier > 1 and not settings.fake_model:
        problems.append("RATE_LIMIT_MULTIPLIER > 1 needs EMPORIO_FAKE_MODEL=1")
    if problems:
        raise WebSettingsRequired(problems)


def _secret_text(value: SecretStr | None) -> str:
    return value.get_secret_value() if value else ""


def load_web_settings(provider: Provider | None = None) -> Settings:
    settings = load_settings(provider)
    require_web_settings(settings)
    return settings
