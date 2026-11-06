from typing import Annotated

from fastapi import APIRouter, Depends

from emporio.api.guards import Session, require_session
from emporio.support.application.warmup import Warmup


def build_warm_router(warmup: Warmup) -> APIRouter:
    router = APIRouter(prefix="/api/warm")

    # Bodiless POST: exempt from require_json (it carries nothing to misread).
    @router.post("")
    def start(_: Annotated[Session, Depends(require_session)]) -> dict[str, object]:
        return warmup.start().to_json()

    @router.get("/status")
    def status(_: Annotated[Session, Depends(require_session)]) -> dict[str, object]:
        return warmup.status().to_json()

    # Public and starts nothing: it feeds the login note.
    @router.get("/expected")
    def expected() -> dict[str, object]:
        return {"mode": warmup.mode.value, "expected_seconds": warmup.expected_seconds}

    return router
