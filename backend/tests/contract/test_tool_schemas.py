import json
from pathlib import Path

from langchain.tools import BaseTool

from emporio.support.infrastructure.agent.tools import build_tools
from tests.unit.support.test_tools import _box

SNAPSHOT = Path(__file__).parent / "snapshots" / "tool_schemas.json"


def _schemas() -> dict[str, object]:
    return {
        t.name: t.tool_call_schema.model_json_schema()["properties"]
        for t in sorted(_tools(), key=lambda t: t.name)
    }


def _tools() -> list[BaseTool]:
    return build_tools(_box())


def test_no_tool_schema_exposes_customer_id_or_runtime() -> None:
    for t in _tools():
        dumped = json.dumps(t.tool_call_schema.model_json_schema())
        assert "customer_id" not in dumped, t.name
        assert "runtime" not in dumped, t.name


def test_tool_descriptions_fit_two_lines() -> None:
    for t in _tools():
        assert len(t.description.splitlines()) <= 2, t.name


def test_tool_schema_snapshot() -> None:
    assert _schemas() == json.loads(SNAPSHOT.read_text())
