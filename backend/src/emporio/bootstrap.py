"""Composition root of the agent: the only place that builds and wires every piece.

`build_agent` returns an `Agent` (the entry point plus a `close`) rather than a context manager,
so a long-lived API process can keep it for its whole life and call `close` from its lifespan.
"""

from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass

from pydantic import SecretStr

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.config import Settings
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
from emporio.support.application.ports import Reply
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.guard import make_classifier
from emporio.support.infrastructure.agent.runner import GraphRunner
from emporio.support.infrastructure.agent.tools import Toolbox, build_tools
from emporio.support.infrastructure.checkpointer import make_checkpointer
from emporio.support.infrastructure.llm.factory import make_chat_model
from emporio.support.infrastructure.metrics_store import PgMetricsStore
from emporio.support.infrastructure.tracing import (
    LangfuseTracerFactory,
    make_langfuse,
    shutdown_tracing,
)


def _secret(value: SecretStr | None) -> str:
    return value.get_secret_value() if value else ""  # load_settings guarantees it is set


@dataclass(frozen=True)
class Agent:
    handle: Callable[[ChannelIdentity, str], Reply]  # a HandleMessage; callable keeps tests easy
    close: Callable[[], None]


def build_agent(settings: Settings) -> Agent:
    """Wire the whole agent. Migrations run first so the pools never see a stale schema."""
    url = database_url()
    with connect(url) as conn:
        apply_migrations(conn)
    setup_checkpointer(url)
    with ExitStack() as stack:
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
        model = make_chat_model(settings)
        saver = make_checkpointer(url)
        stack.enter_context(saver.conn)  # pyright: ignore[reportArgumentType]  # pool is a context manager
        graph = build_graph(model, build_tools(box), make_classifier(model), saver)
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

        handle = HandleMessage(
            GraphRunner(graph, settings, tracer, first_name), PgMetricsStore(pool)
        )
        return Agent(handle, stack.pop_all().close)
