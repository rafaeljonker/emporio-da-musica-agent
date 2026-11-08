from emporio.platform.config.errors import ConfigError
from emporio.platform.config.settings import Settings, secret_text

_MIN_MCP_TOKEN = 32


class InvalidMcpTokens(ConfigError):
    """Names the entry position only: a token value never reaches a message or a log."""

    def __init__(self, position: int, problem: str) -> None:
        super().__init__(f"MCP_TOKENS entry {position}: {problem}")


def mcp_token_identities(settings: Settings) -> dict[str, int | None]:
    """Parse MCP_TOKENS into token -> customer id (None = anonymous)."""
    identities: dict[str, int | None] = {}
    raw = secret_text(settings.mcp_tokens).strip()
    if not raw:
        return identities
    for position, pair in enumerate(raw.split(","), start=1):
        token, sep, identity = pair.strip().partition("=")
        if not sep:
            raise InvalidMcpTokens(position, "must be token=identity")
        if len(token) < _MIN_MCP_TOKEN:
            raise InvalidMcpTokens(position, f"token needs at least {_MIN_MCP_TOKEN} characters")
        if token in identities:
            raise InvalidMcpTokens(position, "duplicate token")
        identity = identity.strip()
        if identity != "anon" and not identity.isdecimal():
            raise InvalidMcpTokens(position, "identity must be a customer id or anon")
        identities[token] = None if identity == "anon" else int(identity)
    return identities
