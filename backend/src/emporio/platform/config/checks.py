from pydantic import SecretStr

from emporio.platform.config.errors import LangfuseRequired, MissingSetting, WebSettingsRequired
from emporio.platform.config.settings import Provider, Settings, _read_settings, secret_text

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
        value = secret_text(value)
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
    elif len(secret_text(settings.session_secret)) < _MIN_SESSION_SECRET:
        problems.append(f"SESSION_SECRET must have at least {_MIN_SESSION_SECRET} characters")
    if settings.rate_limit_multiplier > 1 and not settings.fake_model:
        problems.append("RATE_LIMIT_MULTIPLIER > 1 needs EMPORIO_FAKE_MODEL=1")
    if problems:
        raise WebSettingsRequired(problems)


def load_web_settings(provider: Provider | None = None) -> Settings:
    settings = load_settings(provider)
    require_web_settings(settings)
    return settings
