"""Bearer-token gate for the remote MCP app: the token decides the identity.

The identity lives in a ContextVar for the duration of the request; the MCP tools read it
through `current_mcp_customer`, so the model never passes a customer id.
"""

import hmac
from contextvars import ContextVar

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from emporio.api.errors import ApiErrorCode, error_response
from emporio.api.guards import SlidingWindow, client_ip
from emporio.config import Settings

_customer: ContextVar[int | None] = ContextVar("mcp_customer")
_FAILURES_PER_MINUTE = 10
_CALLS_PER_MINUTE = 60


def current_mcp_customer() -> int | None:
    """The authenticated caller's customer id (None = anonymous). Raises outside a request."""
    return _customer.get()


class McpBearerAuth:
    def __init__(self, app: ASGIApp, identities: dict[str, int | None], settings: Settings) -> None:
        self._app = app
        self._tokens = [(token.encode(), customer) for token, customer in identities.items()]
        self._settings = settings
        self._failures = SlidingWindow(_FAILURES_PER_MINUTE, 60)
        self._calls = SlidingWindow(_CALLS_PER_MINUTE, 60)

    def _match(self, authorization: str) -> tuple[int, int | None] | None:
        scheme, _, given = authorization.partition(" ")
        found: tuple[int, int | None] | None = None
        for index, (token, customer) in enumerate(self._tokens):
            # Every token is compared (no early exit), each in constant time.
            if hmac.compare_digest(given.strip().encode(), token) and found is None:
                found = (index, customer)
        return found if scheme.lower() == "bearer" else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope)
        ip = client_ip(request, self._settings)
        # Locked-out IP: 429 before any compare, so a hit looks like a miss.
        if self._failures.full(ip):
            await error_response(ApiErrorCode.TOO_MANY_ATTEMPTS)(scope, receive, send)
            return
        match = self._match(request.headers.get("authorization", ""))
        if match is None:
            if self._failures.allow(ip):
                reply = error_response(
                    ApiErrorCode.INVALID_TOKEN, headers={"WWW-Authenticate": "Bearer"}
                )
            else:
                reply = error_response(ApiErrorCode.TOO_MANY_ATTEMPTS)
            await reply(scope, receive, send)
            return
        index, customer = match
        if not self._calls.allow(f"token-{index}"):
            await error_response(ApiErrorCode.RATE_LIMITED)(scope, receive, send)
            return
        bound = _customer.set(customer)
        try:
            await self._app(scope, receive, send)
        finally:
            _customer.reset(bound)
