"""The ten agent tools. Plain functions hold the logic; `build_tools` wraps them for LangChain.

Identity (`customer_id`) comes only from `TurnContext`, never from a model argument.
Arguments are strict: money is a JSON number (never `Decimal`'s number-or-string), ids and
counts are bounded integers, unknown fields are rejected. The `Annotated` types below are
shared with the MCP server through the plain functions' signatures.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps
from typing import Annotated, override

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.tools import StructuredTool, ToolException
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, ConfigDict, Field, InstanceOf, ValidationError
from pydantic.json_schema import SkipJsonSchema
from pydantic.v1 import ValidationError as ValidationErrorV1

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

_IN_REAIS = "em reais como número, ex.: 459.90; sem R$ e sem vírgula."
MAX_REAIS = 1_000_000

# strict: a numeric string ("459.90", "R$ 459,90") is rejected, never parsed.
Total = Annotated[
    float, Field(gt=0, le=MAX_REAIS, strict=True, description=f"Valor total {_IN_REAIS}")
]
MaxPrice = Annotated[
    float, Field(gt=0, le=MAX_REAIS, strict=True, description=f"Preço máximo {_IN_REAIS}")
]
Count = Annotated[int, Field(ge=1, le=12, description="Número de parcelas, de 1 a 12, ex.: 4.")]
ProductId = Annotated[
    int, Field(ge=1, description="Id numérico do produto, vindo da busca, ex.: 12.")
]
OrderId = Annotated[int, Field(ge=1, description="Número do pedido, só dígitos, ex.: 1234.")]
EmailOrPhone = Annotated[
    str,
    Field(
        min_length=5,
        max_length=254,
        description="E-mail ou telefone do cadastro, ex.: ana@email.com ou 85999990000.",
    ),
]
Query = Annotated[
    str, Field(min_length=1, max_length=200, description="Nome ou termo, ex.: Rozini RC-104.")
]
Need = Annotated[
    str,
    Field(
        min_length=1,
        max_length=500,
        description="O que o cliente procura, ex.: violão para iniciante.",
    ),
]
Question = Annotated[
    str,
    Field(min_length=1, max_length=500, description="Pergunta sobre a loja, ex.: prazo de troca."),
]


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


def _reais(amount: float) -> Decimal:
    """Through `str`, so 459.9 becomes Decimal("459.9"), not the binary float's expansion."""
    return Decimal(str(amount))


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
    box: Toolbox, ctx: TurnContext, query: Query, max_price: MaxPrice | None = None
) -> ToolOutput:
    ceiling = None if max_price is None else Money(_reais(max_price))
    result = box.search_products(query, ceiling)
    if isinstance(result, NoMatch):
        # Report discontinued products with their status instead of "not found".
        result = box.search_products(query, ceiling, include_unavailable=True)
    return search_json(result, _quotes(box, result), _categories(box))


@_safe
def recommend_products(box: Toolbox, ctx: TurnContext, need: Need) -> ToolOutput:
    result = box.recommend_products(need)
    return search_json(result, _quotes(box, result), _categories(box))


@_safe
def get_product(box: Toolbox, ctx: TurnContext, product_id: ProductId) -> ToolOutput:
    found, quote = box.get_product(product_id)
    return product_json(found, quote, _categories(box).get(product_id, ""))


@_safe
def list_active_promotions(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    categories = _categories(box)
    return [product_json(p, q, categories[p.id]) for p, q in box.list_promotions()]


@_safe
def calc_installments(
    box: Toolbox, ctx: TurnContext, total: Total, count: Count | None = None
) -> ToolOutput:
    if total <= 0:
        return "O valor precisa ser maior que zero."
    money = Money(_reais(total))
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
    box: Toolbox, ctx: TurnContext, order_id: OrderId, email_or_phone: EmailOrPhone | None = None
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
    box: Toolbox, ctx: TurnContext, order_id: OrderId, email_or_phone: EmailOrPhone | None = None
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
def search_policies(box: Toolbox, ctx: TurnContext, question: Question) -> ToolOutput:
    return policy_hits_json(box.search_policies(question, 5))


class _Args(BaseModel):
    """Base of every tool's arguments. `runtime` is injected by ToolNode (it overwrites anything
    the model sends) and hidden from the JSON schema, so identity never comes from the model."""

    model_config = ConfigDict(extra="forbid")
    runtime: SkipJsonSchema[InstanceOf[ToolRuntime]]


class _NoArgs(_Args):
    pass


class _SearchProductsArgs(_Args):
    query: Query
    max_price: MaxPrice | None = None


class _RecommendProductsArgs(_Args):
    need: Need


class _GetProductArgs(_Args):
    product_id: ProductId


class _CalcInstallmentsArgs(_Args):
    total: Total
    count: Count | None = None


class _OrderArgs(_Args):
    order_id: OrderId
    email_or_phone: EmailOrPhone | None = None


class _SearchPoliciesArgs(_Args):
    question: Question


class _StrictTool(StructuredTool):
    """Shows the model the args model itself; LangChain's default rebuilds a copy of it that
    drops `extra="forbid"`, so `additionalProperties: false` would never reach the provider."""

    @property
    @override
    def tool_call_schema(self) -> ArgsSchema:
        return self.args_schema or super().tool_call_schema


def _description(prop: dict[str, object]) -> str:
    options = prop.get("anyOf")
    for option in options if isinstance(options, list) else [prop]:
        if isinstance(option, dict) and isinstance(text := option.get("description"), str):
            return text
    return ""


def _retry_hint(
    name: str, args: type[_Args]
) -> Callable[[ValidationError | ValidationErrorV1], str]:
    """One pt-BR line naming the bad field and its expected form, so the model retries.

    Never echoes the received value: it can be an e-mail, a phone or anything the user typed.
    """
    properties: dict[str, dict[str, object]] = args.model_json_schema().get("properties", {})

    def hint(error: ValidationError | ValidationErrorV1) -> str:
        first = error.errors()[0]
        field = str(first["loc"][0]) if first["loc"] else ""
        logger.warning("tool %s rejected arguments: %s", name, first["type"])
        if field not in properties:
            allowed = ", ".join(properties) or "nenhum"
            return f"Argumento não aceito em {name}; use só: {allowed}."
        expected = _description(properties[field])
        return f"{field} inválido; esperado: {expected} Corrija e chame de novo."

    return hint


def _strict_tool(
    name: str, args: type[_Args], fn: Callable[..., ToolOutput], description: str
) -> BaseTool:
    built = _StrictTool.from_function(fn, name=name, description=description, args_schema=args)
    built.handle_validation_error = _retry_hint(name, args)
    return built


def build_tools(box: Toolbox) -> list[BaseTool]:
    def search_products_tool(
        query: str, runtime: ToolRuntime[TurnContext], max_price: float | None = None
    ) -> ToolOutput:
        return search_products(box, runtime.context, query, max_price)

    def recommend_products_tool(need: str, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return recommend_products(box, runtime.context, need)

    def get_product_tool(product_id: int, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return get_product(box, runtime.context, product_id)

    def list_active_promotions_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return list_active_promotions(box, runtime.context)

    def calc_installments_tool(
        total: float, runtime: ToolRuntime[TurnContext], count: int | None = None
    ) -> ToolOutput:
        return calc_installments(box, runtime.context, total, count)

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

    def store_now_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return store_now(box, runtime.context)

    def search_policies_tool(question: str, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return search_policies(box, runtime.context, question)

    return [
        _strict_tool(
            "search_products",
            _SearchProductsArgs,
            search_products_tool,
            "Busca produtos pelo nome ou termo; max_price opcional é o teto em reais.",
        ),
        _strict_tool(
            "recommend_products",
            _RecommendProductsArgs,
            recommend_products_tool,
            "Recomenda produtos a partir da necessidade descrita pelo cliente.",
        ),
        _strict_tool(
            "get_product",
            _GetProductArgs,
            get_product_tool,
            "Mostra os dados e o preço de um produto pelo id.",
        ),
        _strict_tool(
            "list_active_promotions",
            _NoArgs,
            list_active_promotions_tool,
            "Lista os produtos disponíveis que estão em promoção agora.",
        ),
        _strict_tool(
            "calc_installments",
            _CalcInstallmentsArgs,
            calc_installments_tool,
            "Calcula o parcelamento de um valor; sem count, devolve o máximo de parcelas.",
        ),
        _strict_tool(
            "list_my_orders",
            _NoArgs,
            list_my_orders_tool,
            "Lista os pedidos do cliente identificado, do mais recente ao mais antigo.",
        ),
        _strict_tool(
            "get_order_status",
            _OrderArgs,
            get_order_status_tool,
            "Consulta o status de um pedido; cliente anônimo precisa de e-mail ou telefone.",
        ),
        _strict_tool(
            "check_return_eligibility",
            _OrderArgs,
            check_return_eligibility_tool,
            "Verifica se o pedido pode ser devolvido; anônimo precisa de e-mail ou telefone.",
        ),
        _strict_tool(
            "store_now",
            _NoArgs,
            store_now_tool,
            "Diz se a loja está aberta agora e quando abre de novo.",
        ),
        _strict_tool(
            "search_policies",
            _SearchPoliciesArgs,
            search_policies_tool,
            "Busca nas políticas da loja (troca, garantia, frete, horários).",
        ),
    ]
