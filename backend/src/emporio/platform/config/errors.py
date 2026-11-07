from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emporio.platform.config.settings import Provider


class ConfigError(Exception):
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
