"""Golden cases through the real agent (`make evals PROVIDER=...`); gate: >= 90% pass, 0 tells.

`EVAL_FAKE_MODEL=1` swaps the model for a scripted one that answers everything the same way: it
only proves the harness runs end to end and writes a report (the gate is expected to fail).
Expected facts are derived from the use cases here, never written in the TOML.
"""

import os
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from psycopg import Connection
from psycopg_pool import ConnectionPool

from emporio import bootstrap
from emporio.bootstrap import build_agent
from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.product import Product, ProductStatus
from emporio.catalog.domain.search import Candidates, Exact, SearchResult
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.config import Settings, load_mcp_settings, load_settings
from emporio.embeddings import E5Embedder
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.infrastructure.csv_order_repository import (
    CsvCustomerRepository,
    CsvOrderRepository,
)
from emporio.policies.application.ingest_policies import IngestPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.policies.infrastructure.holidays import STORE_HOLIDAYS
from emporio.policies.infrastructure.pdf_sections import PdfPolicySource
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex
from emporio.shared.clock import FixedClock, SystemClock
from emporio.shared.money import Money
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from evals.verify import Expect, Facts, Verdict, expand, verify
from tests.fakes.fake_chat_model import FakeToolCallingModel

pytestmark = [pytest.mark.eval, pytest.mark.postgres]

EVALS = Path(__file__).parents[2] / "evals"
CASES = tomllib.loads((EVALS / "agent_cases.toml").read_text(encoding="utf-8"))["case"]
GATE_PASS_RATE = 0.90
ORDER_ID = 5
REGRET_CUSTOMER = 14


def _products(found: SearchResult) -> tuple[Product, ...]:
    match found:
        case Exact(product):
            return (product,)
        case Candidates(products):
            return products
    return ()


def _short(product: Product) -> str:
    return " ".join(product.name.split()[:2])  # brand + model, as the spike matched names


def _derive_facts(pool: ConnectionPool, settings: Settings) -> Facts:
    catalog = CsvCatalogRepository()
    orders = CsvOrderRepository()
    customers = CsvCustomerRepository()
    search, get_product = SearchProducts(catalog), GetProduct(catalog)
    today = FixedClock(settings.store_today)

    def quote(product: Product) -> Money:
        return get_product(product.id)[1].final

    violoes = _products(search("violões", Money(Decimal(1000)), include_unavailable=True))
    gd20 = next(p for p in catalog.products() if "GD20" in p.name)
    _, gd20_quote = get_product(gd20.id)
    pix = gd20_quote.pix or gd20_quote.final
    order = orders.by_id(ORDER_ID)
    customer = customers.by_id(order.customer_id) if order else None
    assert order is not None
    assert customer is not None
    latest = ListCustomerOrders(orders)(REGRET_CUSTOMER)[0]
    regret14 = CheckReturnEligibility(orders, today)(latest.id, REGRET_CUSTOMER)
    eligibility5 = CheckReturnEligibility(orders, today)(ORDER_ID, order.customer_id)
    returnable5 = eligibility5.regret_eligible or eligibility5.defect_eligible
    open_now = StoreNow(SystemClock(), STORE_HOLIDAYS)().open
    discontinued = next(p for p in catalog.products() if p.status is ProductStatus.DISCONTINUED)
    recommended = RecommendProducts(catalog, PgProductIndex(pool, E5Embedder()))(
        "algo pra tocar MPB em casa"
    )
    return {
        "viol_ok": tuple(_short(p) for p in violoes if p.is_available),
        "viol_bad": tuple(_short(p) for p in violoes if not p.is_available),
        "gd20_final": gd20_quote.final.format_brl(),
        "gd20_pix": pix.format_brl(),
        "gd20_pix_whole": Money(pix.amount.to_integral_value(rounding="ROUND_DOWN")).format_brl(),
        "regret14": "yes" if regret14.regret_eligible or regret14.defect_eligible else "no",
        "installments900": str(QuoteInstallments()(Money(Decimal(900))).count),
        "order5_email": customer.email,
        "order5_status": order.status.value,
        "order5_tracking": order.tracking_code or "",
        "promo_names": tuple(_short(p) for p, _ in ListPromotions(catalog)()),
        "store_state": "open" if open_now else "closed",
        "store_other": "closed" if open_now else "open",
        "discontinued_name": discontinued.name,
        "takamine_prices": tuple(
            quote(p).format_brl()
            for p in catalog.products()
            if "takamine" in p.name.lower() and p.is_available
        ),
        "regret14_other": "no" if regret14.regret_eligible or regret14.defect_eligible else "yes",
        "takamine_models": tuple(
            p.name.split()[1] for p in catalog.products() if "takamine" in p.name.lower()
        ),
        "return5_other": "no" if returnable5 else "yes",
        "return5": "yes" if returnable5 else "no",
        "recommend_names": tuple(_short(p) for p in _products(recommended)),
    }


@dataclass(frozen=True)
class Outcome:
    name: str
    message: str
    bubbles: tuple[str, ...]
    verdict: Verdict
    tells: tuple[str, ...]
    tools: tuple[str, ...]
    ms: int
    tokens_in: int
    tokens_out: int
    cost_brl: Decimal | None
    trace_id: str


def _expect(case: dict[str, object], facts: Facts) -> Expect:
    def tokens(key: str) -> tuple[str, ...] | None:
        raw = case.get(key)
        if raw is None:
            return None
        assert isinstance(raw, list)
        return tuple(t for token in raw for t in expand(str(token), facts))

    tools = case.get("expect_tools", [])
    assert isinstance(tools, list)
    return Expect(
        expect_tools=tuple(str(t) for t in tools),
        all_of=tokens("all_of") or (),
        any_of=tokens("any_of"),
        none_of=tokens("none_of") or (),
        ask=bool(case.get("ask", False)),
    )


def _turn_row(
    conn: Connection, trace_id: str
) -> tuple[tuple[str, ...], int, int, int, Decimal | None]:
    if not trace_id:  # tracing failed: never match every untraced row
        return (), 0, 0, 0, None
    row = conn.execute(
        "SELECT tools, ms_total, input_tokens, output_tokens, cost_brl FROM turn_metrics"
        " WHERE trace_id = %s ORDER BY id DESC LIMIT 1",
        (trace_id,),
    ).fetchone()
    return (tuple(row[0]), row[1], row[2], row[3], row[4]) if row else ((), 0, 0, 0, None)


def _percentile(values: list[int], q: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))] if ordered else 0


def _report(
    provider: str, model_note: str, model: str, outcomes: list[Outcome], passed: int
) -> str:
    n = len(outcomes)
    ms = [o.ms for o in outcomes]
    costs = [o.cost_brl for o in outcomes if o.cost_brl is not None]
    cost_line = f"R$ {sum(costs) / len(costs):.4f}" if costs else "n/a (no price configured)"
    lines = [
        f"# Agent eval: {provider} ({model}){model_note}",
        f"Run: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        f"- pass: {passed}/{n} ({passed / n:.0%}), gate {GATE_PASS_RATE:.0%}",
        f"- AI tells: {sum(len(o.tells) for o in outcomes)} (gate 0)",
        f"- latency p50/p95: {int(median(ms)) if ms else 0} ms / {_percentile(ms, 0.95)} ms",
        f"- tokens per conversation (in/out): {sum(o.tokens_in for o in outcomes) // n}"
        f" / {sum(o.tokens_out for o in outcomes) // n}",
        f"- R$ per conversation: {cost_line}",
        "",
        "| case | result | tools | tells | ms | tokens in/out | R$ | trace |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        cost = "n/a" if o.cost_brl is None else f"{o.cost_brl:.4f}"
        lines.append(
            f"| {o.name} | {'pass' if o.verdict.passed else 'FAIL'} | {', '.join(o.tools) or '-'}"
            f" | {', '.join(o.tells) or '-'} | {o.ms} | {o.tokens_in}/{o.tokens_out} | {cost}"
            f" | {o.trace_id or '-'} |"
        )
    for o in outcomes:
        if o.verdict.passed and not o.tells:
            continue
        lines += ["", f"## {o.name}", "", f"Customer: {o.message}", ""]
        lines += [f"- {f}" for f in o.verdict.failures] + [f"- tell: {t}" for t in o.tells]
        lines += ["", "```", "\n\n".join(o.bubbles), "```"]
    return "\n".join(lines) + "\n"


def _fake_model(*_: object) -> FakeToolCallingModel:
    """Answers every turn with the same generic line and never calls a tool."""
    reply = "Oi, tudo bem?\n\nPosso ajudar com algum instrumento?"
    return FakeToolCallingModel(messages=iter(AIMessage(reply) for _ in range(10_000)))


def _agent_settings(fake: bool) -> Settings:
    return load_mcp_settings() if fake else load_settings()


def test_agent_golden_cases(
    pg_conn: Connection, pg_pool: ConnectionPool, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = os.environ.get("EVAL_FAKE_MODEL") == "1"
    settings = _agent_settings(fake)
    embedder = E5Embedder()
    IngestPolicies(PdfPolicySource(), PgPolicyIndex(pg_pool, embedder))()
    PgProductIndex(pg_pool, embedder).replace_all(
        CsvCatalogRepository().products(),
        {c.id: c.name for c in CsvCatalogRepository().categories()},
    )
    facts = _derive_facts(pg_pool, settings)
    if fake:
        monkeypatch.setattr(bootstrap, "make_chat_model", _fake_model)
        monkeypatch.setattr(bootstrap, "make_classifier", lambda model: lambda messages: Scope.LOJA)
    agent = build_agent(settings)
    run_id = uuid4().hex[:8]
    outcomes: list[Outcome] = []
    try:
        for _ in range(int(os.environ.get("REPEAT", "1"))):
            for case in CASES:
                customer = case.get("customer_id")
                identity = ChannelIdentity(f"eval-{run_id}-{len(outcomes)}", customer, "s")
                sent = case.get("messages") or [case["message"]]
                assert isinstance(sent, list)
                message = ""
                for (
                    raw
                ) in sent:  # one identity: the thread keeps the history; only the last reply counts
                    message = str(raw).format_map(facts)
                    reply = agent.handle(identity, message)
                tools, ms, tin, tout, cost = _turn_row(pg_conn, reply.trace_id)
                verdict = verify(_expect(case, facts), reply.bubbles, tools)
                outcomes.append(
                    Outcome(
                        case["name"],
                        message,
                        reply.bubbles,
                        verdict,
                        tuple(t.value for t in reply.tells),
                        tools,
                        ms,
                        tin,
                        tout,
                        cost,
                        reply.trace_id,
                    )
                )
    finally:
        agent.close()
    passed = sum(o.verdict.passed for o in outcomes)
    provider = "fake" if fake else settings.provider.value
    note = " (scripted model, harness check only)" if fake else ""
    (EVALS / "reports" / f"{provider}.md").write_text(
        _report(
            provider,
            note,
            str(getattr(settings, f"{settings.provider.value}_model")),
            outcomes,
            passed,
        ),
        encoding="utf-8",
    )
    assert sum(len(o.tells) for o in outcomes) == 0
    assert passed / len(outcomes) >= GATE_PASS_RATE
