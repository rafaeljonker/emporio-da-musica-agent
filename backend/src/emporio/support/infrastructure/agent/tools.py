"""The ten agent tools. Plain functions hold the logic; `build_tools` wraps them for LangChain.

Identity (`customer_id`) comes only from `TurnContext`, never from a model argument.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps

from langchain.tools import BaseTool, ToolRuntime, tool
from langchain_core.tools import ToolException

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.errors import ProductNotFound
from emporio.catalog.domain.installments import InvalidInstallments, max_installments
from emporio.catalog.domain.pricing import PriceQuote
from emporio.catalog.domain.search import Candidates, Exact, NoMatch
from emporio.db import IndexUnavailable
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.domain.errors import OrderNotFound
from emporio.orders.domain.identity import IdentityMismatch
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.shared.errors import DomainError
from emporio.shared.money import Money
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.serializers import (
    eligibility_json,
    installments_json,
    order_json,
    policy_hits_json,
    product_json,
    search_json,
    store_json,
)

logger = logging.getLogger("emporio.support.tools")

type ToolOutput = dict[str, object] | list[dict[str, object]] | str

ORDER_NOT_FOUND = (
    "Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; "
    "peça para conferir o número e o e-mail ou telefone."
)
ASK_ORDER_IDENTITY = "Peça o número do pedido e o e-mail ou telefone do cadastro."
ASK_EMAIL_OR_PHONE = "Peça o e-mail ou telefone do cadastro do pedido."
INSTALLMENTS_NOT_ALLOWED = "Esse parcelamento não é permitido para esse valor."
INDEX_UNAVAILABLE = "Busca indisponível agora; ofereça encaminhar para a equipe."
PRODUCT_NOT_FOUND = "Produto não encontrado."
TOOL_FAILURE = "Não consegui consultar isso agora; ofereça passar o e-mail e o WhatsApp da loja."


class ToolCrashed(ToolException):
    """An unexpected tool failure reduced to name and type: the original message and arguments
    can carry an e-mail or phone, and this text reaches logs and the trace span status."""

    def __init__(self, tool_name: str, error_type: str) -> None:
        super().__init__(f"{tool_name} raised {error_type}")
        self.tool_name = tool_name
        self.error_type = error_type


@dataclass(frozen=True)
class Toolbox:
    search_products: SearchProducts
    recommend_products: RecommendProducts
    get_product: GetProduct
    list_promotions: ListPromotions
    quote_installments: QuoteInstallments
    list_customer_orders: ListCustomerOrders
    get_order_status: GetOrderStatus
    check_return_eligibility: CheckReturnEligibility
    store_now: StoreNow
    search_policies: SearchPolicies
    catalog: CatalogRepository


def _safe[**P](fn: Callable[P, ToolOutput]) -> Callable[P, ToolOutput]:
    """Map domain errors to one short pt-BR line, so the model never sees a traceback."""

    @wraps(fn)
    def run(*args: P.args, **kwargs: P.kwargs) -> ToolOutput:
        try:
            return fn(*args, **kwargs)
        except (IdentityMismatch, OrderNotFound):
            return ORDER_NOT_FOUND
        except ProductNotFound:
            return PRODUCT_NOT_FOUND
        except IndexUnavailable:
            return INDEX_UNAVAILABLE
        except DomainError as err:  # e.g. InvalidMoney
            logger.warning("tool input rejected: %s", err)
            return "Dado inválido."
        except Exception as err:
            raise ToolCrashed(fn.__name__, type(err).__name__) from err

    return run


def _categories(box: Toolbox) -> dict[int, str]:
    names = {c.id: c.name for c in box.catalog.categories()}
    return {p.id: names.get(p.category_id, "") for p in box.catalog.products()}


def _quotes(box: Toolbox, result: Exact | Candidates | NoMatch) -> dict[int, PriceQuote]:
    match result:
        case Exact(product):
            found = (product,)
        case Candidates(products):
            found = products
        case NoMatch():
            found = ()
    return {p.id: box.get_product(p.id)[1] for p in found}


def _product_names(box: Toolbox) -> dict[int, str]:
    return {p.id: p.name for p in box.catalog.products()}


@_safe
def search_products(
    box: Toolbox, ctx: TurnContext, query: str, max_price: Decimal | None = None
) -> ToolOutput:
    ceiling = None if max_price is None else Money(max_price)
    result = box.search_products(query, ceiling)
    if isinstance(result, NoMatch):
        # Report discontinued products with their status instead of "not found".
        result = box.search_products(query, ceiling, include_unavailable=True)
    return search_json(result, _quotes(box, result), _categories(box))


@_safe
def recommend_products(box: Toolbox, ctx: TurnContext, need: str) -> ToolOutput:
    result = box.recommend_products(need)
    return search_json(result, _quotes(box, result), _categories(box))


@_safe
def get_product(box: Toolbox, ctx: TurnContext, product_id: int) -> ToolOutput:
    found, quote = box.get_product(product_id)
    return product_json(found, quote, _categories(box).get(product_id, ""))


@_safe
def list_active_promotions(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    categories = _categories(box)
    return [product_json(p, q, categories[p.id]) for p, q in box.list_promotions()]


@_safe
def calc_installments(
    box: Toolbox, ctx: TurnContext, total: Decimal, count: int | None = None
) -> ToolOutput:
    if total <= 0:
        return "O valor precisa ser maior que zero."
    money = Money(total)
    try:
        return installments_json(box.quote_installments(money, count))
    except InvalidInstallments:
        best = max_installments(money)
        return f"{INSTALLMENTS_NOT_ALLOWED} O máximo é {best.count}x de {best.parcel.format_brl()}."


@_safe
def list_my_orders(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    if ctx.customer_id is None:
        return ASK_ORDER_IDENTITY
    names = _product_names(box)
    return [order_json(o, names) for o in box.list_customer_orders(ctx.customer_id)]


@_safe
def get_order_status(
    box: Toolbox, ctx: TurnContext, order_id: int, email_or_phone: str | None = None
) -> ToolOutput:
    names = _product_names(box)
    if ctx.customer_id is not None:
        # Ownership through the customer's own orders: a foreign id looks unknown.
        mine = next(
            (o for o in box.list_customer_orders(ctx.customer_id) if o.id == order_id), None
        )
        if mine is None:
            raise OrderNotFound(order_id)
        return order_json(mine, names)
    if not email_or_phone:
        return ASK_EMAIL_OR_PHONE
    return order_json(box.get_order_status(order_id, email_or_phone), names)


@_safe
def check_return_eligibility(
    box: Toolbox, ctx: TurnContext, order_id: int, email_or_phone: str | None = None
) -> ToolOutput:
    owner = ctx.customer_id
    if owner is None:
        if not email_or_phone:
            return ASK_EMAIL_OR_PHONE
        owner = box.get_order_status(order_id, email_or_phone).customer_id
    return eligibility_json(box.check_return_eligibility(order_id, owner))


@_safe
def store_now(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    return store_json(box.store_now())


@_safe
def search_policies(box: Toolbox, ctx: TurnContext, question: str) -> ToolOutput:
    return policy_hits_json(box.search_policies(question, 5))


def build_tools(box: Toolbox) -> list[BaseTool]:
    @tool("search_products")
    def search_products_tool(
        query: str, runtime: ToolRuntime[TurnContext], max_price: Decimal | None = None
    ) -> ToolOutput:
        """Busca produtos pelo nome ou termo; max_price opcional é o teto em reais."""
        return search_products(box, runtime.context, query, max_price)

    @tool("recommend_products")
    def recommend_products_tool(need: str, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Recomenda produtos a partir da necessidade descrita pelo cliente."""
        return recommend_products(box, runtime.context, need)

    @tool("get_product")
    def get_product_tool(product_id: int, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Mostra os dados e o preço de um produto pelo id."""
        return get_product(box, runtime.context, product_id)

    @tool("list_active_promotions")
    def list_active_promotions_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Lista os produtos disponíveis que estão em promoção agora."""
        return list_active_promotions(box, runtime.context)

    @tool("calc_installments")
    def calc_installments_tool(
        total: Decimal, runtime: ToolRuntime[TurnContext], count: int | None = None
    ) -> ToolOutput:
        """Calcula o parcelamento de um valor; sem count, devolve o máximo de parcelas."""
        return calc_installments(box, runtime.context, total, count)

    @tool("list_my_orders")
    def list_my_orders_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Lista os pedidos do cliente identificado, do mais recente ao mais antigo."""
        return list_my_orders(box, runtime.context)

    @tool("get_order_status")
    def get_order_status_tool(
        order_id: int, runtime: ToolRuntime[TurnContext], email_or_phone: str | None = None
    ) -> ToolOutput:
        """Consulta o status de um pedido; cliente anônimo precisa de e-mail ou telefone."""
        return get_order_status(box, runtime.context, order_id, email_or_phone)

    @tool("check_return_eligibility")
    def check_return_eligibility_tool(
        order_id: int, runtime: ToolRuntime[TurnContext], email_or_phone: str | None = None
    ) -> ToolOutput:
        """Verifica se o pedido pode ser devolvido; anônimo precisa de e-mail ou telefone."""
        return check_return_eligibility(box, runtime.context, order_id, email_or_phone)

    @tool("store_now")
    def store_now_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Diz se a loja está aberta agora e quando abre de novo."""
        return store_now(box, runtime.context)

    @tool("search_policies")
    def search_policies_tool(question: str, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        """Busca nas políticas da loja (troca, garantia, frete, horários)."""
        return search_policies(box, runtime.context, question)

    tools = [
        search_products_tool,
        recommend_products_tool,
        get_product_tool,
        list_active_promotions_tool,
        calc_installments_tool,
        list_my_orders_tool,
        get_order_status_tool,
        check_return_eligibility_tool,
        store_now_tool,
        search_policies_tool,
    ]
    for built in tools:
        # Malformed arguments: a fixed text, so neither the model-visible message nor the span
        # status echoes the arguments (they may hold an e-mail or phone).
        built.handle_validation_error = TOOL_FAILURE
    return tools
