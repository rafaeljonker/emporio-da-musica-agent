"""Order tools. Identity (`customer_id`) comes only from `TurnContext`, never from a model
argument; an anonymous caller proves ownership with the order's e-mail or phone."""

from collections.abc import Iterable
from typing import Annotated, assert_never

from langchain.tools import BaseTool, ToolRuntime
from pydantic import Field

from emporio.orders.domain.errors import OrdersErrorCode
from emporio.orders.domain.order import Order
from emporio.shared.result import Err, Ok
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.serializers import eligibility_json, order_json
from emporio.support.infrastructure.agent.tools.base import (
    Args,
    NoArgs,
    Toolbox,
    ToolOutput,
    safe,
    strict_tool,
)

ORDER_NOT_FOUND = (
    "Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; "
    "peça para conferir o número e o e-mail ou telefone."
)
ASK_ORDER_IDENTITY = "Peça o número do pedido e o e-mail ou telefone do cadastro."
ASK_EMAIL_OR_PHONE = "Peça o e-mail ou telefone do cadastro do pedido."


def _text(code: OrdersErrorCode) -> str:
    match code:
        case OrdersErrorCode.ORDER_NOT_FOUND:
            return ORDER_NOT_FOUND
        case _:
            assert_never(code)


# Built through the exhaustive match, so a new code without text fails at import.
ORDERS_TEXT: dict[OrdersErrorCode, str] = {code: _text(code) for code in OrdersErrorCode}

OrderId = Annotated[int, Field(ge=1, description="Número do pedido, só dígitos, ex.: 1234.")]
EmailOrPhone = Annotated[
    str,
    Field(
        min_length=5,
        max_length=254,
        description="E-mail ou telefone do cadastro, ex.: ana@email.com ou 85999990000.",
    ),
]


def _product_names(box: Toolbox, orders: Iterable[Order]) -> dict[int, str]:
    ids = {i.product_id for o in orders for i in o.items}
    return {p.id: p.name for p in box.catalog.get_many(ids)}


@safe
def list_my_orders(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    if ctx.customer_id is None:
        return ASK_ORDER_IDENTITY
    orders = box.list_customer_orders(ctx.customer_id)
    names = _product_names(box, orders)
    return [order_json(o, names) for o in orders]


@safe
def get_order_status(
    box: Toolbox, ctx: TurnContext, order_id: OrderId, email_or_phone: EmailOrPhone | None = None
) -> ToolOutput:
    if ctx.customer_id is not None:
        # Ownership through the customer's own orders: a foreign id looks unknown.
        mine = next(
            (o for o in box.list_customer_orders(ctx.customer_id) if o.id == order_id), None
        )
        if mine is None:
            return ORDERS_TEXT[OrdersErrorCode.ORDER_NOT_FOUND]
        return order_json(mine, _product_names(box, (mine,)))
    if not email_or_phone:
        return ASK_EMAIL_OR_PHONE
    match box.get_order_status(order_id, email_or_phone):
        case Ok(found):
            return order_json(found, _product_names(box, (found,)))
        case Err(code):
            return ORDERS_TEXT[code]


@safe
def check_return_eligibility(
    box: Toolbox, ctx: TurnContext, order_id: OrderId, email_or_phone: EmailOrPhone | None = None
) -> ToolOutput:
    owner = ctx.customer_id
    if owner is None:
        if not email_or_phone:
            return ASK_EMAIL_OR_PHONE
        match box.get_order_status(order_id, email_or_phone):
            case Ok(found):
                owner = found.customer_id
            case Err(code):
                return ORDERS_TEXT[code]
    match box.check_return_eligibility(order_id, owner):
        case Ok(eligibility):
            return eligibility_json(eligibility)
        case Err(code):
            return ORDERS_TEXT[code]


class _OrderArgs(Args):
    order_id: OrderId
    email_or_phone: EmailOrPhone | None = None


def orders_tools(box: Toolbox) -> list[BaseTool]:
    def list_my_orders_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return list_my_orders(box, runtime.context)

    def get_order_status_tool(
        order_id: int, runtime: ToolRuntime[TurnContext], email_or_phone: str | None = None
    ) -> ToolOutput:
        return get_order_status(box, runtime.context, order_id, email_or_phone)

    def check_return_eligibility_tool(
        order_id: int, runtime: ToolRuntime[TurnContext], email_or_phone: str | None = None
    ) -> ToolOutput:
        return check_return_eligibility(box, runtime.context, order_id, email_or_phone)

    return [
        strict_tool(
            "list_my_orders",
            NoArgs,
            list_my_orders_tool,
            "Lista os pedidos do cliente identificado, do mais recente ao mais antigo.",
        ),
        strict_tool(
            "get_order_status",
            _OrderArgs,
            get_order_status_tool,
            "Consulta o status de um pedido; cliente anônimo precisa de e-mail ou telefone.",
        ),
        strict_tool(
            "check_return_eligibility",
            _OrderArgs,
            check_return_eligibility_tool,
            "Verifica se o pedido pode ser devolvido; anônimo precisa de e-mail ou telefone.",
        ),
    ]
