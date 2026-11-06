"""Voice-ready lean JSON for tool outputs: plain dicts, money pre-formatted, no scores or notes."""

from collections.abc import Iterable, Mapping

from emporio.catalog.domain.installments import InstallmentPlan
from emporio.catalog.domain.pricing import PriceQuote
from emporio.catalog.domain.product import Product
from emporio.catalog.domain.search import Candidates, Exact, NoMatch
from emporio.orders.domain.order import Order
from emporio.orders.domain.return_policy import ReturnEligibility, ReturnReason
from emporio.policies.application.store_now import StoreStatus
from emporio.policies.domain.policy_chunk import PolicyHit

LEGAL_WARRANTY_NOTE = (
    "A garantia legal de 90 dias para produto durável (CDC art. 26, II) pode valer: "
    "ofereça encaminhar para a equipe."
)
_WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def product_json(product: Product, quote: PriceQuote, category: str) -> dict[str, object]:
    promotion = quote.promotion
    return {
        "id": product.id,
        "name": product.name,
        "category": category,
        "available": product.is_available,
        "status": product.status.value,
        "stock": product.stock,
        "price": {
            "table": quote.table.format_brl(),
            "final": quote.final.format_brl(),
            "promo_percent": None if promotion is None else int(promotion.percent),
            "pix": None if quote.pix is None else quote.pix.format_brl(),
        },
    }


def search_json(
    result: Exact | Candidates | NoMatch,
    quotes: Mapping[int, PriceQuote],
    categories: Mapping[int, str],
    *,
    limit: int = 8,
) -> dict[str, object]:
    match result:
        case Exact(product):
            kind, found = "exact", (product,)
        case Candidates(products):
            kind, found = "candidates", products[:limit]
        case NoMatch():
            kind, found = "none", ()
    return {
        "match": kind,
        "products": [product_json(p, quotes[p.id], categories[p.id]) for p in found],
    }


def order_json(order: Order, product_names: Mapping[int, str]) -> dict[str, object]:
    # Allowlist: `notes` and `customer_id` must never reach the model.
    delivery = order.estimated_delivery
    return {
        "id": order.id,
        "order_date": order.order_date.isoformat(),
        "status": order.status.value,
        "total": order.total.format_brl(),
        "payment_method": order.payment_method,
        "tracking_code": order.tracking_code,
        "estimated_delivery": None if delivery is None else delivery.isoformat(),
        "items": [
            {"name": product_names[i.product_id], "quantity": i.quantity} for i in order.items
        ],
    }


def eligibility_json(e: ReturnEligibility) -> dict[str, object]:
    out: dict[str, object] = {
        "regret_eligible": e.regret_eligible,
        "defect_eligible": e.defect_eligible,
        "delivered_on": None if e.delivered_on is None else e.delivered_on.isoformat(),
        "regret_deadline": None if e.regret_deadline is None else e.regret_deadline.isoformat(),
        "defect_deadline": None if e.defect_deadline is None else e.defect_deadline.isoformat(),
        "reason": e.reason.value,
    }
    if e.reason is ReturnReason.DEFECT_WINDOW_CLOSED:
        out["legal_warranty_note"] = LEGAL_WARRANTY_NOTE
    return out


def policy_hits_json(hits: Iterable[PolicyHit]) -> list[dict[str, object]]:
    return [
        {"section": h.chunk.section_id, "title": h.chunk.title, "text": h.chunk.body} for h in hits
    ]


def store_json(s: StoreStatus) -> dict[str, object]:
    return {
        "open": s.open,
        "now": s.now.isoformat(),
        "next_opening": s.next_opening.isoformat(),
        "next_opening_weekday": _WEEKDAYS[s.next_opening.weekday()],
    }


def installments_json(plan: InstallmentPlan) -> dict[str, object]:
    return {"count": plan.count, "parcel": plan.parcel.format_brl()}
