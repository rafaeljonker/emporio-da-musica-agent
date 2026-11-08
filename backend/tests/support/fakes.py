"""Support test builders: a Toolbox over in-memory fakes."""

from datetime import date

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.product import Product
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.shared.clock import FixedClock
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.tools import Toolbox
from tests.catalog.fakes import FakeCatalogRepository, category, product
from tests.orders.fakes import FakeCustomerRepository, FakeOrderRepository, cust, order
from tests.policies.fakes import InMemoryPolicyIndex

ANON = TurnContext(customer_id=None)


def make_box(*products: Product) -> Toolbox:
    repo = FakeCatalogRepository(products or (product(),), (category(),))
    orders = FakeOrderRepository(
        (
            order(id=1, customer_id=3, order_date=date(2026, 1, 1)),
            order(id=2, customer_id=3, order_date=date(2026, 2, 1)),
            order(id=5, customer_id=4),
        )
    )
    customers = FakeCustomerRepository((cust(id=3), cust(id=4, email="outra@jmail.com")))
    return Toolbox(
        SearchProducts(repo),
        RecommendProducts(repo),
        GetProduct(repo),
        ListPromotions(repo),
        QuoteInstallments(),
        ListCustomerOrders(orders),
        GetOrderStatus(orders, customers),
        CheckReturnEligibility(orders, FixedClock(date(2026, 2, 20))),
        StoreNow(FixedClock(date(2026, 2, 20)), frozenset()),
        SearchPolicies(InMemoryPolicyIndex()),
        repo,
    )
