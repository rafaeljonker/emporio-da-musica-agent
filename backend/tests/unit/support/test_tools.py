from dataclasses import replace
from datetime import date

import pytest

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.product import Product, ProductStatus
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.shared.clock import FixedClock
from emporio.shared.errors import DomainError, StoreUnavailable
from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.tools import Toolbox
from tests.unit.catalog.factories import category, product
from tests.unit.catalog.fakes import FakeCatalogRepository
from tests.unit.orders.factories import cust, order
from tests.unit.orders.fakes import FakeCustomerRepository, FakeOrderRepository
from tests.unit.policies.fakes import InMemoryPolicyIndex

FOREIGN = (
    "Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; "
    "peça para conferir o número e o e-mail ou telefone."
)
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


def test_foreign_order_looks_unknown() -> None:
    box, ctx = make_box(), TurnContext(customer_id=3)

    assert tools.get_order_status(box, ctx, order_id=5) == FOREIGN
    assert tools.get_order_status(box, ctx, order_id=999) == FOREIGN
    assert tools.check_return_eligibility(box, ctx, order_id=5) == FOREIGN


def test_identified_customer_sees_own_order() -> None:
    result = tools.get_order_status(make_box(), TurnContext(customer_id=3), order_id=1)

    assert isinstance(result, dict)
    assert result["id"] == 1


def test_anonymous_order_needs_identity() -> None:
    box = make_box()

    assert tools.list_my_orders(box, ANON) == (
        "Peça o número do pedido e o e-mail ou telefone do cadastro."
    )
    assert "e-mail ou telefone" in str(tools.get_order_status(box, ANON, order_id=1))
    assert tools.get_order_status(box, ANON, order_id=1, email_or_phone="x@y.com") == FOREIGN
    ok = tools.get_order_status(box, ANON, order_id=1, email_or_phone="pedro.oliveira@jmail.com")
    assert isinstance(ok, dict)
    assert ok["id"] == 1


def test_anonymous_return_check_verifies_identity_first() -> None:
    box = make_box()

    assert tools.check_return_eligibility(box, ANON, 1, "errado@x.com") == FOREIGN
    ok = tools.check_return_eligibility(box, ANON, 1, "pedro.oliveira@jmail.com")
    assert isinstance(ok, dict)
    assert "regret_eligible" in ok


def test_list_my_orders_newest_first() -> None:
    result = tools.list_my_orders(make_box(), TurnContext(customer_id=3))

    assert isinstance(result, list)
    assert [o["id"] for o in result] == [2, 1]


def test_search_reports_discontinued_product() -> None:
    gone = product(id=1, name="Violao Antigo", status=ProductStatus.DISCONTINUED, stock=0)

    result = tools.search_products(make_box(gone), ANON, query="violao antigo")

    assert isinstance(result, dict)
    found = result["products"]
    assert isinstance(found, list)
    assert found[0]["status"] == "discontinued"


def test_calc_installments_error_names_the_maximum() -> None:
    result = tools.calc_installments(make_box(), ANON, total=100, count=10)

    assert isinstance(result, str)
    assert result.startswith("Esse parcelamento não é permitido para esse valor.")
    assert "O máximo é 2x" in result


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (StoreUnavailable(), "Busca indisponível agora; ofereça encaminhar para a equipe."),
    ],
)
def test_domain_errors_become_tool_text(error: Exception, text: str) -> None:
    @tools._safe
    def boom() -> str:
        raise error

    assert str(boom()).startswith(text)


def test_unknown_product_is_product_not_found_text() -> None:
    assert tools.get_product(make_box(), ANON, product_id=99) == "Produto não encontrado."


def test_calc_installments_huge_total_returns_text() -> None:
    result = tools.calc_installments(make_box(), ANON, total=1e30)

    assert isinstance(result, str)


def test_calc_installments_needs_positive_total() -> None:
    result = tools.calc_installments(make_box(), ANON, total=0)

    assert result == "O valor precisa ser maior que zero."


def test_generic_domain_error_is_logged_not_echoed(caplog: pytest.LogCaptureFixture) -> None:
    class Secret(DomainError):
        def __init__(self) -> None:
            super().__init__("segredo interno")

    @tools._safe
    def boom() -> str:
        raise Secret

    with caplog.at_level("WARNING", logger="emporio.support.tools"):
        result = boom()

    assert result == "Dado inválido."
    assert "segredo interno" in caplog.text


def test_unexpected_exception_is_reduced_to_tool_name_and_type() -> None:
    def broken(question: str, k: int) -> object:
        raise RuntimeError("segredo@exemplo.com")

    box = replace(make_box(), search_policies=broken)  # pyright: ignore[reportArgumentType]
    with pytest.raises(tools.ToolCrashed) as crash:
        tools.search_policies(box, ANON, "troca")
    assert str(crash.value) == "search_policies raised RuntimeError"
