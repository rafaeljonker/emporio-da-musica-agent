import json
from pathlib import Path
from typing import Any

import pytest
from google.genai.types import Type
from langchain.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_google_genai._function_utils import convert_to_genai_function_declarations

from emporio.support.infrastructure.agent.tools import build_tools
from tests.support.fakes import make_box

pytestmark = pytest.mark.contract

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


MONEY = {"total", "max_price"}
IDS = {"order_id", "product_id"}


def _openai_params(t: BaseTool) -> dict[str, Any]:
    return convert_to_openai_tool(t)["function"]["parameters"]


def _branch(prop: dict[str, Any]) -> dict[str, Any]:
    """The non-null branch of an optional field (or the field itself)."""
    options = [o for o in prop.get("anyOf", [prop]) if o.get("type") != "null"]
    assert len(options) == 1, prop
    return options[0]


def test_every_tool_forbids_unknown_arguments() -> None:
    for t in _tools():
        assert _openai_params(t)["additionalProperties"] is False, t.name


def test_money_is_a_bounded_number_never_a_string() -> None:
    seen: set[str] = set()
    for t in _tools():
        for name, prop in _openai_params(t)["properties"].items():
            if name in MONEY:
                seen.add(name)
                branch = _branch(prop)
                assert branch["type"] == "number", (t.name, name)
                assert branch["exclusiveMinimum"] == 0, (t.name, name)
                assert "maximum" in branch, (t.name, name)
                assert "459.90" in json.dumps(prop), (t.name, name)  # pt-BR example
    assert seen == MONEY


def test_counts_and_ids_are_bounded_integers() -> None:
    for t in _tools():
        for name, prop in _openai_params(t)["properties"].items():
            branch = _branch(prop)
            if name == "count":
                assert (branch["type"], branch["minimum"], branch["maximum"]) == ("integer", 1, 12)
            if name in IDS:
                assert (branch["type"], branch["minimum"]) == ("integer", 1), (t.name, name)


def test_every_argument_has_a_description_and_strings_are_bounded() -> None:
    for t in _tools():
        for name, prop in _openai_params(t)["properties"].items():
            assert "description" in json.dumps(prop), (t.name, name)
            branch = _branch(prop)
            if branch["type"] == "string":
                assert branch["minLength"] >= 1, (t.name, name)
                assert "maxLength" in branch, (t.name, name)


def test_gemini_sees_money_as_a_number() -> None:
    calc = next(t for t in _tools() if t.name == "calc_installments")
    # Same path as ChatGoogleGenerativeAI.bind_tools: OpenAI format first, then Gemini's.
    openai = convert_to_openai_tool(calc)
    [declaration] = convert_to_genai_function_declarations([openai])[0].function_declarations or []
    assert declaration.parameters is not None
    assert declaration.parameters.properties is not None
    total = declaration.parameters.properties["total"]
    assert total.type == Type.NUMBER
    assert total.any_of is None
