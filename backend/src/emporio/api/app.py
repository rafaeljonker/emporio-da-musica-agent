from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from emporio.api.auth import build_auth_router
from emporio.api.catalog import build_catalog_router
from emporio.api.chat import build_chat_router
from emporio.api.identity import build_identity_router
from emporio.api.warm import build_warm_router
from emporio.config import Settings, require_web_settings
from emporio.support.application.ports import CatalogAdmin, ChatAgent
from emporio.support.application.warmup import Warmup


def create_app(
    agent: ChatAgent,
    warmup: Warmup,
    settings: Settings,
    catalog: CatalogAdmin,
    *,
    static_dir: Path | None = None,
) -> FastAPI:
    require_web_settings(settings)
    secret = settings.session_secret.get_secret_value() if settings.session_secret else ""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            agent.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    # ponytail: stateless signed cookie, so logout cannot revoke a copied cookie. Starlette re-sets
    # the cookie only when the session changes, so max_age runs from login or the last customer
    # switch (it does not slide); upgrade = server-side sid denylist or an absolute issued_at check.
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="emporio_session",
        same_site="strict",
        https_only=settings.session_https_only,
        max_age=settings.session_max_age_seconds,
    )
    app.include_router(build_auth_router(settings, warmup))
    app.include_router(build_chat_router(agent, settings))
    app.include_router(build_catalog_router(catalog, settings))
    app.include_router(build_identity_router(agent))
    app.include_router(build_warm_router(warmup))
    # Mounted last so it never shadows /api.
    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
