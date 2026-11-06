"""MCP server exposing the same ten tools the agent uses (stdio).

Tool logic is not duplicated: each MCP tool wraps the plain function in `agent.tools`.
Identity: the installed fastmcp offers `Depends()`, but a closure over one `TurnContext`
fixed at launch (`EMPORIO_MCP_CUSTOMER_ID` on stdio) gives the same result with less
machinery, and the wrapper signature drops `box`/`ctx`, so no identity reaches the schema.
Domain errors come back as the same pt-BR text the agent sees (the plain functions never
raise for them); `mask_error_details=True` hides anything unexpected.
Langfuse tracing does not apply here: there is no LLM and no turn on this path, so the
"Langfuse mandatory" rule (every agent turn is traced) is not bypassed.
"""

import inspect
from collections.abc import Callable
from functools import wraps

from fastmcp import FastMCP

from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.tools import Toolbox, ToolOutput

_PLAIN = (
    tools.search_products,
    tools.recommend_products,
    tools.get_product,
    tools.list_active_promotions,
    tools.calc_installments,
    tools.list_my_orders,
    tools.get_order_status,
    tools.check_return_eligibility,
    tools.store_now,
    tools.search_policies,
)


def _bind(
    fn: Callable[..., ToolOutput], box: Toolbox, ctx: TurnContext
) -> Callable[..., ToolOutput]:
    """Same function minus its first two parameters (box, ctx), so the schema omits them."""

    @wraps(fn)
    def run(**kwargs: object) -> ToolOutput:
        return fn(box, ctx, **kwargs)

    params = list(inspect.signature(fn).parameters.values())[2:]
    vars(run)["__signature__"] = inspect.Signature(params)
    run.__annotations__ = {p.name: p.annotation for p in params}
    return run


def build_mcp(box: Toolbox, *, customer_id: int | None) -> FastMCP:
    server = FastMCP("emporio-da-musica", mask_error_details=True)
    ctx = TurnContext(customer_id=customer_id)
    descriptions = {t.name: t.description for t in tools.build_tools(box)}
    for fn in _PLAIN:
        server.tool(_bind(fn, box, ctx), name=fn.__name__, description=descriptions[fn.__name__])
    return server
