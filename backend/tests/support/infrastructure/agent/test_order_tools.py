from dataclasses import replace

import pytest

from emporio.orders.infrastructure.csv_order_repository import OrdersDataError
from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.context import TurnContext
from tests.support.fakes import ANON, make_box

FOREIGN = (
    "Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; "
    "peça para conferir o número e o e-mail ou telefone."
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


def test_data_error_is_tool_failure_not_invalid_data() -> None:
    def bad_csv(customer_id: int) -> object:
        raise OrdersDataError("orders.csv", 2, ValueError("segredo@exemplo.com"))

    box = replace(make_box(), list_customer_orders=bad_csv)  # pyright: ignore[reportArgumentType]
    with pytest.raises(tools.ToolCrashed) as crash:
        tools.list_my_orders(box, TurnContext(customer_id=3))
    assert str(crash.value) == "list_my_orders raised OrdersDataError"
