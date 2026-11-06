from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from emporio.api.auth import build_auth_router
from emporio.config import Settings, WebSettingsRequired
from emporio.support.application.ports import ChatAgent
from emporio.support.application.warmup import Warmup


def create_app(
    agent: ChatAgent, warmup: Warmup, settings: Settings, *, static_dir: Path | None = None
) -> FastAPI:
    if settings.session_secret is None:
        raise WebSettingsRequired(["SESSION_SECRET is not set"])

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            agent.close()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="emporio_session",
        same_site="strict",
        https_only=settings.session_https_only,
        max_age=settings.session_max_age_seconds,
    )
    app.include_router(build_auth_router(settings, warmup))
    # Mounted last so it never shadows /api.
    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
