"""guard -> agent <-> tools, as an explicit StateGraph.

The system prompt is rebuilt per model call from `TurnContext` (customer name, today) and the
turn's scope: static prefix first, dynamic tail last, so prefix caching still hits. Trimming
works on a copy; the checkpointed state keeps the full history.
"""

from collections.abc import Callable, Sequence
from typing import NotRequired

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.prompt import scope_note, system_prompt

ABUSE_REPLY = (
    "Vamos manter a conversa respeitosa. "
    "Posso te ajudar com instrumentos, pedidos ou dúvidas da loja."
)


class AgentState(MessagesState):
    scope: NotRequired[Scope | None]  # set by the guard on every turn


type AgentGraph = CompiledStateGraph[AgentState, TurnContext, AgentState, AgentState]


def build_graph(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    classify: Callable[[Sequence[BaseMessage]], Scope],
    checkpointer: BaseCheckpointSaver[str],
    *,
    max_history_tokens: int = 3000,
) -> AgentGraph:
    def guard(state: AgentState) -> dict[str, Scope]:
        return {"scope": classify(state["messages"])}

    def abuse_reply(state: AgentState) -> dict[str, list[BaseMessage]]:
        return {"messages": [AIMessage(ABUSE_REPLY)]}

    def agent(state: AgentState, runtime: Runtime[TurnContext]) -> dict[str, list[BaseMessage]]:
        ctx = runtime.context
        scope = state.get("scope")
        head = system_prompt(ctx.customer_name, ctx.today)
        note = "" if scope is None else scope_note(scope)
        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=max_history_tokens,
            start_on="human",
            end_on=("human", "tool"),
        )
        prompt = [SystemMessage(f"{head}\n\n{note}" if note else head), *history]
        runner = model.bind_tools(tools) if scope is Scope.LOJA else model
        return {"messages": [runner.invoke(prompt)]}

    def route_scope(state: AgentState) -> str:
        return "abuse_reply" if state.get("scope") is Scope.ABUSO else "agent"

    graph = StateGraph(AgentState, context_schema=TurnContext)
    graph.add_node("guard", guard)
    graph.add_node("abuse_reply", abuse_reply)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", route_scope, ["abuse_reply", "agent"])
    graph.add_edge("abuse_reply", END)
    graph.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
