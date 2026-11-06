import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from emporio.api.guards import Session, SlidingWindow, require_json, require_session
from emporio.support.application.ports import ChatAgent


class IdentityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)] | None


def build_identity_router(agent: ChatAgent) -> APIRouter:
    router = APIRouter(prefix="/api")
    # Keyed by the login id: a switch rotates `sid`, so a per-sid window would never fill.
    switches = SlidingWindow(10, 60)

    @router.get("/customers")
    def customers(_: Annotated[Session, Depends(require_session)]) -> list[dict[str, object]]:
        return [{"id": c.id, "name": c.name, "city": c.city} for c in agent.demo_customers]

    @router.put("/identity", dependencies=[Depends(require_json)])
    def set_identity(
        body: IdentityIn, request: Request, _: Annotated[Session, Depends(require_session)]
    ) -> dict[str, int | None]:
        if not switches.allow(str(request.session.get("lid", ""))):
            raise HTTPException(status_code=429, detail="too_many_switches")
        if body.customer_id not in {None, *(c.id for c in agent.demo_customers)}:
            raise HTTPException(status_code=404, detail="unknown_customer")
        # A new sid starts a new thread, so the previous customer's history is never reused.
        request.session.update({"sid": secrets.token_urlsafe(16), "customer_id": body.customer_id})
        return {"customer_id": body.customer_id}

    return router
