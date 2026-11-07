"""What every tool shares: the use-case box, the error wrapper and the strict LangChain wrapper.

Arguments are strict: money is a JSON number (never `Decimal`'s number-or-string), ids and
counts are bounded integers, unknown fields are rejected.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import override

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.tools import StructuredTool, ToolException
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, ConfigDict, InstanceOf, ValidationError
from pydantic.json_schema import SkipJsonSchema
from pydantic.v1 import ValidationError as ValidationErrorV1

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.application.search_products import SearchProducts
from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.application.store_now import StoreNow
from emporio.shared.errors import StoreUnavailable

logger = logging.getLogger("emporio.support.tools")

type ToolOutput = dict[str, object] | list[dict[str, object]] | str

INDEX_UNAVAILABLE = "Busca indisponível agora; ofereça encaminhar para a equipe."
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


def safe[**P](fn: Callable[P, ToolOutput]) -> Callable[P, ToolOutput]:
    """Expected failures are values the tools already turned into text. Only an unreachable
    store keeps its own line; anything else is a bug (or bad data/config) and becomes
    `ToolCrashed`, which the graph answers with TOOL_FAILURE."""

    @wraps(fn)
    def run(*args: P.args, **kwargs: P.kwargs) -> ToolOutput:
        try:
            return fn(*args, **kwargs)
        except StoreUnavailable:
            return INDEX_UNAVAILABLE
        except Exception as err:
            raise ToolCrashed(fn.__name__, type(err).__name__) from err

    return run


class Args(BaseModel):
    """Base of every tool's arguments. `runtime` is injected by ToolNode (it overwrites anything
    the model sends) and hidden from the JSON schema, so identity never comes from the model."""

    model_config = ConfigDict(extra="forbid")
    runtime: SkipJsonSchema[InstanceOf[ToolRuntime]]


class NoArgs(Args):
    pass


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
    name: str, args: type[Args]
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


def strict_tool(
    name: str, args: type[Args], fn: Callable[..., ToolOutput], description: str
) -> BaseTool:
    built = _StrictTool.from_function(fn, name=name, description=description, args_schema=args)
    built.handle_validation_error = _retry_hint(name, args)
    return built
