"""Where an error code becomes an HTTP status: one exhaustive map per code set.

Bodies are always `{"detail": "<code>"}`; the frontend turns the code into pt-BR text.
"""

import logging
from enum import StrEnum
from typing import assert_never

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from emporio.catalog.domain.errors import CatalogErrorCode

logger = logging.getLogger("emporio.api")


class ApiErrorCode(StrEnum):
    """Refusals the API itself makes. The values are wire codes: change none of them."""

    TOO_MANY_ATTEMPTS = "too_many_attempts"
    INVALID_CREDENTIALS = "invalid_credentials"
    UNAUTHENTICATED = "unauthenticated"
    JSON_REQUIRED = "json_required"
    TOO_MANY_MESSAGES = "too_many_messages"
    TURN_IN_PROGRESS = "turn_in_progress"
    TOO_MANY_SWITCHES = "too_many_switches"
    UNKNOWN_CUSTOMER = "unknown_customer"
    TOO_MANY_WRITES = "too_many_writes"
    INVALID_TOKEN = "invalid_token"  # noqa: S105  # a wire code, not a secret
    RATE_LIMITED = "rate_limited"


def _catalog_status(code: CatalogErrorCode) -> int:
    match code:
        case CatalogErrorCode.PRODUCT_NOT_FOUND | CatalogErrorCode.PRODUCT_NOT_OWNED:
            return 404
        case (
            CatalogErrorCode.UNKNOWN_CATEGORY
            | CatalogErrorCode.NAME_TAKEN_BY_STORE
            | CatalogErrorCode.PROMO_CLAIM
            | CatalogErrorCode.INSTALLMENTS_NOT_ALLOWED
        ):
            return 422
        case CatalogErrorCode.CATALOG_FULL:
            return 409
        case CatalogErrorCode.CATALOG_UNAVAILABLE:
            return 503
        case _:
            assert_never(code)


def _api_status(code: ApiErrorCode) -> int:
    match code:
        case (
            ApiErrorCode.INVALID_CREDENTIALS
            | ApiErrorCode.UNAUTHENTICATED
            | ApiErrorCode.INVALID_TOKEN
        ):
            return 401
        case ApiErrorCode.UNKNOWN_CUSTOMER:
            return 404
        case ApiErrorCode.TURN_IN_PROGRESS:
            return 409
        case ApiErrorCode.JSON_REQUIRED:
            return 415
        case (
            ApiErrorCode.TOO_MANY_ATTEMPTS
            | ApiErrorCode.TOO_MANY_MESSAGES
            | ApiErrorCode.TOO_MANY_SWITCHES
            | ApiErrorCode.TOO_MANY_WRITES
            | ApiErrorCode.RATE_LIMITED
        ):
            return 429
        case _:
            assert_never(code)


# Built through the exhaustive matches, so a new code without a status fails at import.
CATALOG_HTTP: dict[CatalogErrorCode, int] = {c: _catalog_status(c) for c in CatalogErrorCode}
API_HTTP: dict[ApiErrorCode, int] = {c: _api_status(c) for c in ApiErrorCode}


def http_error(code: ApiErrorCode | CatalogErrorCode) -> HTTPException:
    """For routes and dependencies: `raise http_error(code)`."""
    status = API_HTTP[code] if isinstance(code, ApiErrorCode) else CATALOG_HTTP[code]
    return HTTPException(status_code=status, detail=code.value)


def error_response(code: ApiErrorCode, headers: dict[str, str] | None = None) -> JSONResponse:
    """For raw ASGI code (the /mcp guard), where there is no route to raise from."""
    return JSONResponse({"detail": code.value}, API_HTTP[code], headers=headers)


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """A bug answers a fixed body: the message and stack stay in the server log."""
    logger.exception("unexpected error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse({"detail": "internal_error"}, 500)
