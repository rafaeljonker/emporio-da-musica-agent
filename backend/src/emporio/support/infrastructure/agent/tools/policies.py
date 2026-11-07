"""Store policy tools: opening hours now, and search over the policy documents."""

from typing import Annotated

from langchain.tools import BaseTool, ToolRuntime
from pydantic import Field

from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.serializers import policy_hits_json, store_json
from emporio.support.infrastructure.agent.tools.base import (
    Args,
    NoArgs,
    Toolbox,
    ToolOutput,
    safe,
    strict_tool,
)

Question = Annotated[
    str,
    Field(min_length=1, max_length=500, description="Pergunta sobre a loja, ex.: prazo de troca."),
]


@safe
def store_now(box: Toolbox, ctx: TurnContext) -> ToolOutput:
    return store_json(box.store_now())


@safe
def search_policies(box: Toolbox, ctx: TurnContext, question: Question) -> ToolOutput:
    return policy_hits_json(box.search_policies(question, 5))


class _SearchPoliciesArgs(Args):
    question: Question


def policies_tools(box: Toolbox) -> list[BaseTool]:
    def store_now_tool(runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return store_now(box, runtime.context)

    def search_policies_tool(question: str, runtime: ToolRuntime[TurnContext]) -> ToolOutput:
        return search_policies(box, runtime.context, question)

    return [
        strict_tool(
            "store_now",
            NoArgs,
            store_now_tool,
            "Diz se a loja está aberta agora e quando abre de novo.",
        ),
        strict_tool(
            "search_policies",
            _SearchPoliciesArgs,
            search_policies_tool,
            "Busca nas políticas da loja (troca, garantia, frete, horários).",
        ),
    ]
