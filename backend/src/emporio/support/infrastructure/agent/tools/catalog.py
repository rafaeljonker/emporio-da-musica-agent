"""Catalog tools: search, recommend, product detail, promotions and installments.

The `Annotated` types below are shared with the MCP server through the plain functions'
signatures.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal
from typing import Annotated, assert_never

from langchain.tools import BaseTool, ToolRuntime
from pydantic import Field

from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.installments import max_installments
from emporio.catalog.domain.pricing import (
    PriceQuote,
    Promotion,
    best_active_promotion,
    quote_price,
)
from emporio.catalog.domain.product import Product
from emporio.catalog.domain.search import Candidates, Exact, NoMatch
from emporio.shared.money import Money
from emporio.shared.result import Err, Ok
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.serializers import (
    installments_json,
    product_json,
    search_json,
)
from emporio.support.infrastructure.agent.tools.base import (
    INDEX_UNAVAILABLE,
    TOOL_FAILURE,
    Args,
    NoArgs,
    Toolbox,
    ToolOutput,
    safe,
    strict_tool,
)

INSTALLMENTS_NOT_ALLOWED = "Esse parcelamento não é permitido para esse valor."
PRODUCT_NOT_FOUND = "Produto não encontrado."


def _text(code: CatalogErrorCode) -> str:
    match code:
        case CatalogErrorCode.PRODUCT_NOT_FOUND:
            return PRODUCT_NOT_FOUND
        case CatalogErrorCode.INSTALLMENTS_NOT_ALLOWED:
            return INSTALLMENTS_NOT_ALLOWED
        case CatalogErrorCode.CATALOG_UNAVAILABLE:
            return INDEX_UNAVAILABLE
        # Write-path codes: no tool writes, so reaching one here is a bug.
        case (
            CatalogErrorCode.UNKNOWN_CATEGORY
            | CatalogErrorCode.PRODUCT_NOT_OWNED
            | CatalogErrorCode.CATALOG_FULL
            | CatalogErrorCode.NAME_TAKEN_BY_STORE
            | CatalogErrorCode.PROMO_CLAIM
        ):
            return TOOL_FAILURE
        case _:
            assert_never(code)


# Built through the exhaustive match, so a new code without text fails at import.
CATALOG_TEXT: dict[CatalogErrorCode, str] = {code: _text(code) for code in CatalogErrorCode}

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


def _reais(amount: float) -> Decimal:
    """Through `str`, so 459.9 becomes Decimal("459.9"), not the binary float's expansion."""
    return Decimal(str(amount))


def _categories(box: Toolbox, products: Iterable[Product]) -> dict[int, str]:
    names = {c.id: c.name for c in box.catalog.categories()}
    return {p.id: names.get(p.category_id, "") for p in products}


def _found(result: Exact | Candidates | NoMatch) -> tuple[Product, ...]:
    match result:
        case Exact(product):
            return (product,)
        case Candidates(products):
            return products
        case NoMatch():
            return ()


def _quotes(box: Toolbox, products: Sequence[Product]) -> dict[int, PriceQuote]:
    groups: defaultdict[int, list[Promotion]] = defaultdict(list)
    for promo in box.catalog.promotions_for([p.id for p in products]):
        groups[promo.product_id].append(promo)
    return {p.id: quote_price(p, best_active_promotion(groups[p.id])) for p in products}


@safe
def search_products(
    box: Toolbox, ctx: TurnContext, query: Query, max_price: MaxPrice | None = None
) -> ToolOutput:
    ceiling = None if max_price is None else Money(_reais(max_price))
    result = box.search_products(query, ceiling)
    if isinstance(result, NoMatch):
        # Report discontinued products with their status instead of "not found".
        result = box.search_products(query, ceiling, include_unavailable=True)
    found = _found(result)
    return search_json(result, _quotes(box, found), _categories(box, found))


@safe
def recommend_products(box: Toolbox, ctx: TurnContext, need: Need) -> ToolOutput:
    result = box.recommend_products(need)
    found = _found(result)
    return search_json(result, _quotes(box, found), _categories(box, found))


@safe
def get_product(box: Toolbox, ctx: TurnContext, product_id: ProductId) -> ToolOutput:
    match box.get_product(product_id):
        case Ok((found, quote)):
            return product_json(found, quote, _categories(box, (found,))[product_id])
        case Err(code):
            return CATALOG_TEXT[code]


@safe
def list_active_promotions(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    items = box.list_promotions()
    categories = _categories(box, (p for p, _ in items))
    return [product_json(p, q, categories[p.id]) for p, q in items]


@safe
def calc_installments(
    box: Toolbox, ctx: TurnContext, total: Total, count: Count | None = None
) -> ToolOutput:
    money = Money(_reais(total))
    match box.quote_installments(money, count):
        case Ok(plan):
            return installments_json(plan)
        case Err(code):
            best = max_installments(money)
            parcel = best.parcel.format_brl()
            return f"{CATALOG_TEXT[code]} O máximo é {best.count}x de {parcel}."


class _SearchProductsArgs(Args):
    query: Query
    max_price: MaxPrice | None = None


class _RecommendProductsArgs(Args):
    need: Need


class _GetProductArgs(Args):
    product_id: ProductId


class _CalcInstallmentsArgs(Args):
    total: Total
    count: Count | None = None


def catalog_tools(box: Toolbox) -> list[BaseTool]:
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

    return [
        strict_tool(
            "search_products",
            _SearchProductsArgs,
            search_products_tool,
            "Busca produtos pelo nome ou termo; max_price opcional é o teto em reais.",
        ),
        strict_tool(
            "recommend_products",
            _RecommendProductsArgs,
            recommend_products_tool,
            "Recomenda produtos a partir da necessidade descrita pelo cliente.",
        ),
        strict_tool(
            "get_product",
            _GetProductArgs,
            get_product_tool,
            "Mostra os dados e o preço de um produto pelo id.",
        ),
        strict_tool(
            "list_active_promotions",
            NoArgs,
            list_active_promotions_tool,
            "Lista os produtos disponíveis que estão em promoção agora.",
        ),
        strict_tool(
            "calc_installments",
            _CalcInstallmentsArgs,
            calc_installments_tool,
            "Calcula o parcelamento de um valor; sem count, devolve o máximo de parcelas.",
        ),
    ]
