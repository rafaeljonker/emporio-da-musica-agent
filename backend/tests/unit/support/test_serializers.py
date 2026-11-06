from datetime import date, datetime

from emporio.catalog.domain.installments import installment_plan
from emporio.catalog.domain.pricing import quote_price
from emporio.catalog.domain.search import Candidates, Exact, NoMatch
from emporio.orders.domain.order import OrderItem
from emporio.orders.domain.return_policy import ReturnEligibility, ReturnReason
from emporio.policies.application.store_now import StoreStatus
from emporio.policies.domain.policy_chunk import PolicyChunk, PolicyHit
from emporio.shared.clock import STORE_TZ
from emporio.support.infrastructure.agent.serializers import (
    eligibility_json,
    installments_json,
    order_json,
    policy_hits_json,
    product_json,
    search_json,
    store_json,
)
from tests.unit.catalog.factories import m, product, promo
from tests.unit.orders.factories import order

WARRANTY = (
    "A garantia legal de 90 dias para produto durável (CDC art. 26, II) pode valer: "
    "ofereça encaminhar para a equipe."
)


def _eligibility(reason: ReturnReason) -> ReturnEligibility:
    d = date(2026, 2, 10)
    return ReturnEligibility(False, False, d, d, d, reason)


def test_product_json_shape():
    p = product(price="1000")
    out = product_json(p, quote_price(p, None), "Violões")
    assert out == {
        "id": 1,
        "name": "Violao",
        "category": "Violões",
        "available": True,
        "status": "active",
        "stock": 5,
        "price": {"table": "R$ 1.000", "final": "R$ 1.000", "promo_percent": None, "pix": "R$ 950"},
    }


def test_pix_absent_with_active_promotion():
    p = product(price="1000")
    price = product_json(p, quote_price(p, promo(percent="10")), "Violões")["price"]
    assert price == {"table": "R$ 1.000", "final": "R$ 900", "promo_percent": 10, "pix": None}


def test_money_is_voice_formatted():
    p = product(price="2199")
    price = product_json(p, quote_price(p, None), "Violões")["price"]
    assert isinstance(price, dict)
    assert price["table"] == "R$ 2.199"
    assert price["pix"] == "R$ 2.089,05"


def test_search_json_match_kinds_and_limit():
    ps = tuple(product(id=i) for i in range(1, 11))
    quotes = {p.id: quote_price(p, None) for p in ps}
    cats = {p.id: "Violões" for p in ps}
    exact = search_json(Exact(ps[0]), quotes, cats)
    many = search_json(Candidates(ps), quotes, cats)
    none = search_json(NoMatch(), quotes, cats)
    assert exact["match"] == "exact"
    assert many["match"] == "candidates"
    assert isinstance(many["products"], list)
    assert len(many["products"]) == 8
    assert none == {"match": "none", "products": []}


def test_order_json_never_contains_notes():
    o = order(notes="cliente reclamou", tracking_code="BR1", items=(OrderItem(1, 2),))
    out = order_json(o, {1: "Violao"})
    assert "notes" not in out
    assert "customer_id" not in out
    assert out == {
        "id": 1,
        "order_date": "2026-02-01",
        "status": "delivered",
        "total": "R$ 1.000",
        "payment_method": "pix",
        "tracking_code": "BR1",
        "estimated_delivery": "2026-02-10",
        "items": [{"name": "Violao", "quantity": 2}],
    }


def test_legal_warranty_note_only_when_defect_window_closed():
    closed = eligibility_json(_eligibility(ReturnReason.DEFECT_WINDOW_CLOSED))
    other = eligibility_json(_eligibility(ReturnReason.WITHIN_DEFECT_WINDOW))
    assert closed["legal_warranty_note"] == WARRANTY
    assert "legal_warranty_note" not in other
    assert other["reason"] == "within_defect_window"
    assert other["regret_deadline"] == "2026-02-10"


def test_eligibility_none_dates_stay_none():
    out = eligibility_json(
        ReturnEligibility(False, False, None, None, None, ReturnReason.CANCELLED)
    )
    assert out["delivered_on"] is None


def test_store_json_weekday_ptbr():
    monday = datetime(2026, 11, 9, 9, 0, tzinfo=STORE_TZ)
    sunday = datetime(2026, 11, 8, 12, 0, tzinfo=STORE_TZ)
    out = store_json(StoreStatus(open=False, now=sunday, next_opening=monday))
    assert out == {
        "open": False,
        "now": sunday.isoformat(),
        "next_opening": monday.isoformat(),
        "next_opening_weekday": "segunda-feira",
    }


def test_policy_hits_drop_score():
    hit = PolicyHit(PolicyChunk("3.1", "Trocas", "Pós-venda", "texto"), 0.9)
    assert policy_hits_json([hit]) == [{"section": "3.1", "title": "Trocas", "text": "texto"}]


def test_installments_json():
    out = installments_json(installment_plan(m("1200"), 12))
    assert out == {"count": 12, "parcel": "R$ 100"}
