import json
from pathlib import Path
from typing import Any

from langchain.tools import BaseTool

from emporio.support.infrastructure.agent.tools import build_tools
from tests.unit.support.test_tools import make_box

SNAPSHOT = Path(__file__).parent / "snapshots" / "tool_schemas.json"


def _json_schema(t: BaseTool) -> dict[str, Any]:
    schema = t.tool_call_schema
    if isinstance(schema, dict):
        return schema
    # pyright: ignore below: langchain types this union with the pydantic.v1 BaseModel.
    return schema.model_json_schema()  # pyright: ignore[reportAttributeAccessIssue]


def _schemas() -> dict[str, object]:
    return {t.name: _json_schema(t)["properties"] for t in sorted(_tools(), key=lambda t: t.name)}


def _tools() -> list[BaseTool]:
    return build_tools(make_box())


def test_no_tool_schema_exposes_customer_id_or_runtime() -> None:
    for t in _tools():
        dumped = json.dumps(_json_schema(t))
        assert "customer_id" not in dumped, t.name
        assert "runtime" not in dumped, t.name


def test_tool_descriptions_fit_two_lines() -> None:
    for t in _tools():
        assert len(t.description.splitlines()) <= 2, t.name


def test_tool_schema_snapshot() -> None:
    assert _schemas() == json.loads(SNAPSHOT.read_text())
