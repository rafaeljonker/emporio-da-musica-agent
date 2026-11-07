from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from emporio.api.auth import build_auth_router
from emporio.api.catalog import build_catalog_router
from emporio.api.chat import build_chat_router
from emporio.api.errors import unexpected_error
from emporio.api.identity import build_identity_router
from emporio.api.mcp_auth import McpBearerAuth
from emporio.api.warm import build_warm_router
from emporio.catalog.application.admin import CatalogAdmin
from emporio.platform.config import Settings, mcp_token_identities, require_web_settings
from emporio.support.application.ports import ChatAgent
from emporio.support.application.warmup import Warmup


def create_app(
    agent: ChatAgent,
    warmup: Warmup,
    settings: Settings,
    catalog: CatalogAdmin,
    *,
    static_dir: Path | None = None,
    mcp: Starlette | None = None,
) -> FastAPI:
    """`mcp` (the streamable HTTP app at /mcp) is served only when MCP_TOKENS is set."""
    require_web_settings(settings)
    secret = settings.session_secret.get_secret_value() if settings.session_secret else ""
    identities = mcp_token_identities(settings)
    mcp = mcp if identities else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # A mounted app's lifespan never runs on its own: the MCP session manager starts here.
        mcp_life: AbstractAsyncContextManager[object] = (
            mcp.router.lifespan_context(mcp) if mcp else nullcontext()
        )
        try:
            async with mcp_life:
                yield
        finally:
            agent.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(Exception, unexpected_error)
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
    if mcp is not None:
        # Exactly /mcp (/mcp/ is not served); routed before the static mount, which takes "/".
        app.router.routes.append(Route("/mcp", McpBearerAuth(mcp, identities, settings)))
    # Mounted last so it never shadows /api.
    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
