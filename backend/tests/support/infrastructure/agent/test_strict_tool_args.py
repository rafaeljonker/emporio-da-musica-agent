"""Tool arguments through the real graph: valid calls run, malformed ones get a retry hint."""

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.tools import build_tools
from emporio.support.infrastructure.agent.tools.base import TOOL_FAILURE
from tests.fakes.fake_chat_model import FakeToolCallingModel
from tests.support.fakes import make_box


def _tool_reply(name: str, args: dict[str, object], customer_id: int | None = 3) -> str:
    call = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "c1"}])
    model = FakeToolCallingModel(messages=iter([call, AIMessage("ok")]))
    graph = build_graph(model, build_tools(make_box()), lambda _m: Scope.LOJA, InMemorySaver())
    messages: list[BaseMessage] = graph.invoke(
        {"messages": [HumanMessage("oi")]},
        RunnableConfig(configurable={"thread_id": "t"}),
        context=TurnContext(customer_id=customer_id),
    )["messages"]
    replies = [m for m in messages if isinstance(m, ToolMessage)]
    assert len(replies) == 1
    return str(replies[0].content)


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("search_products", {"query": "violao", "max_price": 2000}),
        ("search_products", {"query": "violao"}),
        ("recommend_products", {"need": "violão para iniciante"}),
        ("get_product", {"product_id": 1}),
        ("list_active_promotions", {}),
        ("calc_installments", {"total": 459.90, "count": 4}),
        ("calc_installments", {"total": 459}),
        ("list_my_orders", {}),
        ("get_order_status", {"order_id": 1}),
        ("check_return_eligibility", {"order_id": 1}),
        ("store_now", {}),
        ("search_policies", {"question": "prazo de troca"}),
    ],
)
def test_valid_args_still_work(name: str, args: dict[str, object]) -> None:
    reply = _tool_reply(name, args)

    assert reply != TOOL_FAILURE
    assert "inválido" not in reply


def test_installments_with_float_total_quotes_in_decimal() -> None:
    reply = _tool_reply("calc_installments", {"total": 459.90, "count": 4})

    assert "114.98" in reply or "114,98" in reply  # 459.90 / 4 rounded up, never float noise


def test_brl_string_total_gets_a_retry_hint() -> None:
    reply = _tool_reply("calc_installments", {"total": "R$ 459,90", "count": 4})

    assert reply != TOOL_FAILURE
    assert "total" in reply
    assert "459.90" in reply
    assert "R$ 459,90" not in reply  # the bad value is never echoed


@pytest.mark.parametrize(
    ("name", "args", "field"),
    [
        ("calc_installments", {"total": 459.9, "count": 13}, "count"),
        ("calc_installments", {"total": 0}, "total"),
        ("get_order_status", {"order_id": 0}, "order_id"),
        ("get_product", {"product_id": "RC-104"}, "product_id"),
        ("search_products", {"query": ""}, "query"),
        ("get_order_status", {"order_id": 1, "email_or_phone": "x" * 300}, "email_or_phone"),
    ],
)
def test_out_of_range_args_name_the_field(name: str, args: dict[str, object], field: str) -> None:
    reply = _tool_reply(name, args)

    assert reply != TOOL_FAILURE
    assert field in reply
    assert len(reply.splitlines()) == 1


def test_unknown_argument_is_rejected_without_echoing_it() -> None:
    reply = _tool_reply("calc_installments", {"total": 100, "cpf": "123.456.789-00"})

    assert reply != TOOL_FAILURE
    assert "123.456" not in reply
    assert "total" in reply
