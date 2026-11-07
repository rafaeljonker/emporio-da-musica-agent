"""Web entry point: `uvicorn --factory emporio.web:create_web_app`."""

from fastapi import FastAPI

from emporio.api.app import create_app
from emporio.api.mcp_auth import current_mcp_customer
from emporio.bootstrap import build_agent, build_remote_mcp, build_warmup
from emporio.platform.config import load_web_settings
from emporio.platform.paths import REPO_ROOT


def create_web_app() -> FastAPI:
    settings = load_web_settings()
    agent = build_agent(settings)
    warmup = build_warmup(settings, agent.reply_p50_seconds)
    return create_app(
        agent,
        warmup,
        settings,
        agent.catalog_admin,
        static_dir=REPO_ROOT / "frontend" / "dist",
        mcp=build_remote_mcp(agent, settings, current_mcp_customer),
    )
