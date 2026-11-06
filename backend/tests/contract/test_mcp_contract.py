import asyncio
import json
from typing import Any

from fastmcp import Client
from langchain.tools import BaseTool

from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.mcp.server import build_mcp
from tests.unit.support.test_tools import make_box


def _agent_schema(t: BaseTool) -> dict[str, Any]:
    schema = t.tool_call_schema
    return schema if isinstance(schema, dict) else schema.model_json_schema()  # pyright: ignore[reportAttributeAccessIssue]


def _mcp_tools() -> list[Any]:
    async def run() -> list[Any]:
        async with Client(build_mcp(make_box(), customer_id=3)) as client:
            return await client.list_tools()

    return asyncio.run(run())


def _shape(schema: dict[str, Any]) -> dict[str, object]:
    props = {name: sorted(_types(p)) for name, p in schema.get("properties", {}).items()}
    return {"properties": props, "required": sorted(schema.get("required", []))}


def _types(prop: dict[str, Any]) -> set[str]:
    options = prop.get("anyOf", [prop])
    return {str(o.get("type")) for o in options}


def test_mcp_schemas_equal_agent_schemas() -> None:
    agent = {t.name: _shape(_agent_schema(t)) for t in tools.build_tools(make_box())}
    mcp = {t.name: _shape(t.input_schema) for t in _mcp_tools()}

    assert mcp == agent


def test_mcp_schema_has_no_customer_id() -> None:
    for t in _mcp_tools():
        assert "customer_id" not in json.dumps(t.input_schema), t.name


def test_mcp_call_returns_same_json() -> None:
    box, ctx = make_box(), TurnContext(customer_id=3)

    async def run() -> tuple[object, object]:
        async with Client(build_mcp(box, customer_id=3)) as client:
            now = await client.call_tool("store_now", {})
            found = await client.call_tool("search_products", {"query": "violao"})
            return now.structured_content, found.structured_content

    now, found = asyncio.run(run())

    assert now == json.loads(json.dumps(tools.store_now(box, ctx)))
    assert found == json.loads(json.dumps(tools.search_products(box, ctx, "violao")))
