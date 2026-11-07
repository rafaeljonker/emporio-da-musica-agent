from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from emporio.platform.config.errors import InvalidSettings
from emporio.platform.paths import REPO_ROOT


class Provider(StrEnum):
    GEMMA = "gemma"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


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

    warm_expected_seconds_gpu: int = 210  # H100 FP8 warm-cache boot measured 204 s (phase 6)
    warm_expected_seconds_local: int = 120
    # A READY older than this is probed again on login/warm (phase 6: Modal's scaledown window).
    warm_ready_ttl_seconds: int = 300
    # Fake warm-up for e2e: the model "becomes ready" after N seconds (0 = ready at once).
    fake_warm_seconds: int = Field(default=0, validation_alias="EMPORIO_FAKE_WARM_SECONDS")
    # A WarmMode value; a plain string so platform never imports a context.
    fake_warm_mode: Literal["modal_gpu", "local_cpu", "provider_api"] = Field(
        default="modal_gpu", validation_alias="EMPORIO_FAKE_WARM_MODE"
    )

    demo_email: str | None = None
    demo_password: SecretStr | None = None
    session_secret: SecretStr | None = None
    session_https_only: bool = True
    session_max_age_seconds: int = 28800
    # Shared with the Cloudflare Worker: only a request carrying it may name the client IP.
    proxy_secret: SecretStr | None = None
    # Remote MCP at /mcp: comma-separated `token=identity` (customer id or `anon`); empty = off.
    mcp_tokens: SecretStr | None = None
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


def _secret_text(value: SecretStr | None) -> str:
    return value.get_secret_value() if value else ""
