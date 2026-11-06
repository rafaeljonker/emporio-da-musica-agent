"""Composition root of the agent: the only place that builds and wires every piece.

`build_agent` returns an `Agent` (the entry point plus a `close`) rather than a context manager,
so a long-lived API process can keep it for its whole life and call `close` from its lifespan.
"""

import time
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass

from psycopg_pool import ConnectionPool
from pydantic import SecretStr

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.config import Provider, Settings, UnknownCustomer
from emporio.db import connect, database_url, make_pool
from emporio.embeddings import E5Embedder
from emporio.migrate import apply_migrations, setup_checkpointer
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.infrastructure.csv_order_repository import (
    CsvCustomerRepository,
    CsvOrderRepository,
)
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.policies.infrastructure.holidays import STORE_HOLIDAYS
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex
from emporio.shared.clock import FixedClock, SystemClock
from emporio.support.application.handle_message import HandleMessage
from emporio.support.application.ports import DemoCustomer, Reply
from emporio.support.application.warmup import WarmMode, WarmStage, Warmup
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.guard import make_classifier
from emporio.support.infrastructure.agent.runner import GraphRunner
from emporio.support.infrastructure.agent.tools import Toolbox, build_tools
from emporio.support.infrastructure.checkpointer import make_checkpointer
from emporio.support.infrastructure.llm.factory import make_chat_model
from emporio.support.infrastructure.llm.scripted import ScriptedChatModel
from emporio.support.infrastructure.mcp.server import build_mcp
from emporio.support.infrastructure.metrics_store import PgMetricsStore
from emporio.support.infrastructure.tracing import (
    LangfuseTracerFactory,
    make_langfuse,
    shutdown_tracing,
)
from emporio.support.infrastructure.warmup import ProbeWarmup, ReadyWarmup, vllm_health_probe

# Order 7 (in the regret window), order 5 (out of it), shipped, pending, two cancelled,
# confirmed, and one customer with no orders.
DEMO_CUSTOMER_IDS = (14, 5, 2, 8, 3, 7, 11, 19)


def _secret(value: SecretStr | None) -> str:
    return value.get_secret_value() if value else ""  # load_settings guarantees it is set


def _store_scope(_messages: object) -> Scope:
    """Classifier of the scripted model: every turn takes the store path."""
    return Scope.LOJA


@dataclass(frozen=True)
class Agent:
    handle: Callable[[ChannelIdentity, str], Reply]  # a HandleMessage; callable keeps tests easy
    close: Callable[[], None]
    customer_exists: Callable[[int], bool]
    demo_customers: tuple[DemoCustomer, ...] = ()
    reply_p50_seconds: Callable[[], float | None] = lambda: None


def build_toolbox(
    stack: ExitStack, url: str, settings: Settings
) -> tuple[Toolbox, CsvCustomerRepository, ConnectionPool]:
    """Wire the ten tools' dependencies; shared by the agent and the MCP server."""
    pool = stack.enter_context(make_pool(url))
    embedder = E5Embedder()
    catalog = CsvCatalogRepository()
    orders = CsvOrderRepository()
    customers = CsvCustomerRepository()
    box = Toolbox(
        SearchProducts(catalog),
        RecommendProducts(catalog, PgProductIndex(pool, embedder)),
        GetProduct(catalog),
        ListPromotions(catalog),
        QuoteInstallments(),
        ListCustomerOrders(orders),
        GetOrderStatus(orders, customers),
        CheckReturnEligibility(orders, FixedClock(settings.store_today)),
        StoreNow(SystemClock(), STORE_HOLIDAYS),
        SearchPolicies(PgPolicyIndex(pool, embedder)),
        catalog,
    )
    return box, customers, pool


def build_agent(settings: Settings) -> Agent:
    """Wire the whole agent. Migrations run first so the pools never see a stale schema."""
    url = database_url()
    with connect(url) as conn:
        apply_migrations(conn)
    setup_checkpointer(url)
    with ExitStack() as stack:
        box, customers, pool = build_toolbox(stack, url, settings)
        if settings.fake_model:
            model = ScriptedChatModel()
            classify = _store_scope
        else:
            model = make_chat_model(settings)
            classify = make_classifier(model)
        saver = make_checkpointer(url)
        stack.enter_context(saver.conn)  # pyright: ignore[reportArgumentType]  # pool is a context manager
        graph = build_graph(model, build_tools(box), classify, saver)
        langfuse = make_langfuse(settings)
        stack.callback(shutdown_tracing)
        tracer = LangfuseTracerFactory(
            langfuse,
            _secret(settings.langfuse_salt),
            _secret(settings.langfuse_public_key),
        )

        def first_name(customer_id: int) -> str | None:
            customer = customers.by_id(customer_id)
            return customer.name.split()[0] if customer and customer.name.strip() else None

        store = PgMetricsStore(pool)
        handle = HandleMessage(GraphRunner(graph, settings, tracer, first_name), store)
        demo = tuple(
            DemoCustomer(c.id, c.name, c.city)
            for c in (customers.by_id(i) for i in DEMO_CUSTOMER_IDS)
            if c is not None
        )
        return Agent(
            handle,
            stack.pop_all().close,
            lambda cid: customers.by_id(cid) is not None,
            demo,
            lambda: store.reply_p50_seconds(settings.provider_name),
        )


def build_warmup(settings: Settings, reply_p50: Callable[[], float | None]) -> Warmup:
    """The honest warm-up: a vLLM health probe for Gemma, ready at once for provider APIs."""
    if settings.fake_model:
        if settings.fake_warm_seconds <= 0:
            return ReadyWarmup(WarmMode.PROVIDER_API, reply_p50)
        began: list[float] = []

        def fake_probe() -> bool:
            if not began:
                began.append(time.monotonic())
            return time.monotonic() - began[0] >= settings.fake_warm_seconds

        local = settings.fake_warm_mode is WarmMode.LOCAL_CPU
        return ProbeWarmup(
            fake_probe,
            settings.fake_warm_mode,
            settings.warm_expected_seconds_local if local else settings.warm_expected_seconds_gpu,
            reply_p50,
            stage=WarmStage.MODEL_LOADING if local else WarmStage.SERVER_STARTING,
            interval_seconds=0.5,
            ready_ttl_seconds=settings.warm_ready_ttl_seconds,
        )
    if settings.provider is Provider.GEMMA:
        probe = vllm_health_probe(settings.vllm_base_url or "", _secret(settings.vllm_api_key))
        return ProbeWarmup(
            probe,
            WarmMode.MODAL_GPU,
            settings.warm_expected_seconds_gpu,
            reply_p50,
            ready_ttl_seconds=settings.warm_ready_ttl_seconds,
        )
    return ReadyWarmup(WarmMode.PROVIDER_API, reply_p50)


def run_mcp(settings: Settings, customer_id: int | None) -> None:
    """Serve the tools over stdio. No model, graph, checkpointer or Langfuse needed.

    Migrations are not applied here: the schema is expected to exist (`make mcp` runs `make db`).
    """
    with ExitStack() as stack:
        box, customers, _ = build_toolbox(stack, database_url(), settings)
        if customer_id is not None and customers.by_id(customer_id) is None:
            raise UnknownCustomer(customer_id)
        build_mcp(box, customer_id=customer_id).run()
