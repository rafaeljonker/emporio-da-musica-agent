"""The ten agent tools, one module per context. Plain functions hold the logic (and are what
the MCP server wraps); `build_tools` wraps them for LangChain."""

from langchain.tools import BaseTool

from emporio.support.infrastructure.agent.tools.base import (
    Toolbox,
    ToolCrashed,
    ToolOutput,
)
from emporio.support.infrastructure.agent.tools.catalog import (
    calc_installments,
    catalog_tools,
    get_product,
    list_active_promotions,
    recommend_products,
    search_products,
)
from emporio.support.infrastructure.agent.tools.orders import (
    ASK_ORDER_IDENTITY,
    check_return_eligibility,
    get_order_status,
    list_my_orders,
    orders_tools,
)
from emporio.support.infrastructure.agent.tools.policies import (
    policies_tools,
    search_policies,
    store_now,
)

PLAIN = (
    search_products,
    recommend_products,
    get_product,
    list_active_promotions,
    calc_installments,
    list_my_orders,
    get_order_status,
    check_return_eligibility,
    store_now,
    search_policies,
)


def build_tools(box: Toolbox) -> list[BaseTool]:
    return [*catalog_tools(box), *orders_tools(box), *policies_tools(box)]


__all__ = [
    "ASK_ORDER_IDENTITY",
    "PLAIN",
    "ToolCrashed",
    "ToolOutput",
    "Toolbox",
    "build_tools",
    "calc_installments",
    "check_return_eligibility",
    "get_order_status",
    "get_product",
    "list_active_promotions",
    "list_my_orders",
    "recommend_products",
    "search_policies",
    "search_products",
    "store_now",
]
