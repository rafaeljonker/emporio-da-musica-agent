import logging
from collections.abc import Iterator, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, StringConstraints

from emporio.api.guards import (
    Session,
    SlidingWindow,
    ThreadLocks,
    require_json,
    require_session,
)
from emporio.support.application.ports import ChatAgent, TurnMetrics
from emporio.support.domain.bubbles import pace_bubbles
from emporio.support.domain.channel_identity import ChannelIdentity

logger = logging.getLogger("emporio.api.chat")

ACTIONS = {
    "search_products": "busca no catálogo",
    "get_product": "busca no catálogo",
    "recommend_products": "busca no catálogo",
    "list_active_promotions": "busca no catálogo",
    "calc_installments": "cálculo de parcelas",
    "list_my_orders": "consulta de pedido",
    "get_order_status": "consulta de pedido",
    "check_return_eligibility": "consulta de troca",
    "store_now": "horário da loja",
    "search_policies": "consulta às políticas",
}
PRICED = "Estimado pelo preço de lista do provedor"
UNPRICED = "Custo de GPU ainda não medido"


def action_label(tools: Sequence[str]) -> str:
    labels = dict.fromkeys(ACTIONS[t] for t in tools if t in ACTIONS)
    return " + ".join(labels) or "sem ferramenta"


def _metrics_payload(m: TurnMetrics) -> dict[str, object]:
    cost = (
        None if m.cost_brl is None else str(m.cost_brl.quantize(Decimal("0.0001"), ROUND_HALF_UP))
    )
    return {
        "input_tokens": m.input_tokens,
        "output_tokens": m.output_tokens,
        "ms_model": m.ms_total,
        "ms_guard": m.ms_guard,
        "ms_llm": m.ms_llm,
        "ms_tools": m.ms_tools,
        "cost_brl": cost,
        "cost_basis": UNPRICED if cost is None else PRICED,
        "action": action_label(m.tools),
    }


def _event(name: str, data: dict[str, object]) -> ServerSentEvent:
    return ServerSentEvent(event=name, data=data)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


def build_chat_router(agent: ChatAgent) -> APIRouter:
    router = APIRouter(prefix="/api/chat")
    per_session = SlidingWindow(20, 600)
    locks = ThreadLocks()

    def turn_slot(
        session: Annotated[Session, Depends(require_session)],
    ) -> Iterator[ChannelIdentity]:
        # A yield dependency also runs when body validation fails or the client drops
        # before the stream starts, so the lock cannot leak.
        if not per_session.allow(session.sid):
            raise HTTPException(status_code=429, detail="too_many_messages")
        identity = ChannelIdentity("web", session.customer_id, session.sid)
        thread_id = identity.thread_id()
        token = locks.try_acquire(thread_id)
        if token is None:
            raise HTTPException(status_code=409, detail="turn_in_progress")
        try:
            yield identity
        finally:
            locks.release(thread_id, token)

    @router.post("", response_class=EventSourceResponse, dependencies=[Depends(require_json)])
    def chat(
        body: ChatIn, identity: Annotated[ChannelIdentity, Depends(turn_slot)]
    ) -> Iterator[ServerSentEvent]:
        yield _event("typing", {})
        sent = 0
        try:
            reply = agent.handle(identity, body.text)
            if reply.failed or reply.metrics is None:
                yield _event("error", {"partial": False})
                return
            for text, delay in zip(reply.bubbles, pace_bubbles(reply.bubbles), strict=True):
                yield _event("bubble", {"kind": "text", "text": text, "delay_ms": delay})
                sent += 1
            yield _event("metrics", _metrics_payload(reply.metrics))
        except Exception:
            logger.exception("chat turn failed")
            yield _event("error", {"partial": sent > 0})
            return
        yield _event("done", {"trace_id": reply.trace_id})

    return router
