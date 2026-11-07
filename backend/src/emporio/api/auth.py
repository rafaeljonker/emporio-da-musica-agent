import hmac
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict

from emporio.api.errors import ApiErrorCode, http_error
from emporio.api.guards import (
    Session,
    SlidingWindow,
    client_ip,
    require_json,
    require_session,
)
from emporio.platform.config import Settings
from emporio.support.application.warmup import Warmup


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


def _same(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())


def build_auth_router(settings: Settings, warmup: Warmup) -> APIRouter:
    router = APIRouter(prefix="/api/auth")
    # Without PROXY_SECRET every client shares the proxy IP, so keep an overall backstop.
    per_ip = SlidingWindow(5 * settings.rate_limit_multiplier, 60)
    overall = SlidingWindow(30 * settings.rate_limit_multiplier, 60)
    demo_password = settings.demo_password.get_secret_value() if settings.demo_password else None

    @router.post("/login", dependencies=[Depends(require_json)])
    def login(body: LoginIn, request: Request) -> dict[str, object]:
        if not (per_ip.allow(client_ip(request, settings)) and overall.allow("*")):
            raise http_error(ApiErrorCode.TOO_MANY_ATTEMPTS)
        if (
            settings.demo_email is None
            or demo_password is None
            or not (_same(body.email, settings.demo_email) & _same(body.password, demo_password))
        ):
            raise http_error(ApiErrorCode.INVALID_CREDENTIALS)
        request.session.clear()
        request.session.update(
            {
                "sid": secrets.token_urlsafe(16),
                "lid": secrets.token_urlsafe(16),
                "customer_id": None,
            }
        )
        return {"warm": warmup.start().to_json()}

    @router.post("/logout", status_code=204)
    def logout(request: Request) -> Response:
        request.session.clear()
        return Response(status_code=204)

    @router.get("/me")
    def me(session: Annotated[Session, Depends(require_session)]) -> dict[str, object]:
        return {"customer_id": session.customer_id, "warm": warmup.status().to_json()}

    return router
