import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from emporio.api.guards import Session, require_json, require_session
from emporio.support.application.ports import ChatAgent


class IdentityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)] | None


def build_identity_router(agent: ChatAgent) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/customers")
    def customers(_: Annotated[Session, Depends(require_session)]) -> list[dict[str, object]]:
        return [{"id": c.id, "name": c.name, "city": c.city} for c in agent.demo_customers]

    @router.put("/identity", dependencies=[Depends(require_json)])
    def set_identity(
        body: IdentityIn, request: Request, _: Annotated[Session, Depends(require_session)]
    ) -> dict[str, int | None]:
        if body.customer_id is not None and not agent.customer_exists(body.customer_id):
            raise HTTPException(status_code=404, detail="unknown_customer")
        # A new sid starts a new thread, so the previous customer's history is never reused.
        request.session.update({"sid": secrets.token_urlsafe(16), "customer_id": body.customer_id})
        return {"customer_id": body.customer_id}

    return router
