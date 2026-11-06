"""Web entry point: `uvicorn --factory emporio.web:create_web_app`."""

from fastapi import FastAPI

from emporio.api.app import create_app
from emporio.bootstrap import build_agent
from emporio.config import load_web_settings
from emporio.paths import REPO_ROOT
from emporio.support.application.warmup import WarmMode
from emporio.support.infrastructure.warmup import ReadyWarmup


def create_web_app() -> FastAPI:
    settings = load_web_settings()
    # Task 6 swaps in build_warmup.
    warmup = ReadyWarmup(WarmMode.PROVIDER_API, lambda: None)
    return create_app(
        build_agent(settings), warmup, settings, static_dir=REPO_ROOT / "frontend" / "dist"
    )
