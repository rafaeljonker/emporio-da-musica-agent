"""MCP server exposing the same ten tools the agent uses (stdio and streamable HTTP).

Tool logic is not duplicated: each MCP tool wraps a plain function in `agent.tools.PLAIN`.
Identity: each call asks a context provider for its `TurnContext`: a fixed one on stdio
(`EMPORIO_MCP_CUSTOMER_ID`), the bearer token's identity on HTTP. The wrapper signature
drops `box`/`ctx`, so no identity reaches the schema.
Domain errors come back as the same pt-BR text the agent sees (the plain functions never
raise for them); `mask_error_details=True` hides anything unexpected.
Langfuse tracing does not apply here: there is no LLM and no turn on this path, so the
"Langfuse mandatory" rule (every agent turn is traced) is not bypassed.
"""

import inspect
from collections.abc import Callable
from functools import wraps

from fastmcp import FastMCP
from starlette.applications import Starlette

from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.tools import Toolbox, ToolOutput


def _bind(
    fn: Callable[..., ToolOutput], box: Toolbox, context: Callable[[], TurnContext]
) -> Callable[..., ToolOutput]:
    """Same function minus its first two parameters (box, ctx), so the schema omits them."""

    @wraps(fn)
    def run(**kwargs: object) -> ToolOutput:
        return fn(box, context(), **kwargs)

    params = list(inspect.signature(fn).parameters.values())[2:]
    vars(run)["__signature__"] = inspect.Signature(params)
    run.__annotations__ = {p.name: p.annotation for p in params}
    return run


def build_mcp(box: Toolbox, context: Callable[[], TurnContext]) -> FastMCP:
    server = FastMCP("emporio-da-musica", mask_error_details=True)
    descriptions = {t.name: t.description for t in tools.build_tools(box)}
    for fn in tools.PLAIN:
        server.tool(
            _bind(fn, box, context), name=fn.__name__, description=descriptions[fn.__name__]
        )
    return server


def build_mcp_http_app(box: Toolbox, customer_id: Callable[[], int | None]) -> Starlette:
    """Streamable HTTP at exactly `/mcp`, stateless with JSON replies (one container, no
    session affinity behind the Worker). `customer_id` is read on every tool call."""
    server = build_mcp(box, lambda: TurnContext(customer_id=customer_id()))
    return server.http_app(path="/mcp", stateless_http=True, json_response=True)
