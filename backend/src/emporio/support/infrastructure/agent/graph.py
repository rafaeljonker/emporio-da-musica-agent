"""guard -> agent <-> tools, as an explicit StateGraph.

The system prompt is rebuilt per model call from `TurnContext` (customer name, today) and the
turn's scope: static prefix first, dynamic tail last, so prefix caching still hits. Trimming
works on a copy and never touches the current turn; the checkpointed state keeps the full history.
"""

import logging
from collections.abc import Callable, Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.context import TurnContext
from emporio.support.infrastructure.agent.prompt import scope_note, system_prompt

logger = logging.getLogger("emporio.support.tools")

MAX_TOOL_ROUNDS = 5
TOOL_FAILURE = "Não consegui consultar isso agora; ofereça passar o e-mail e o WhatsApp da loja."
NO_MORE_TOOLS = "Responda com o que você já tem, sem chamar mais ferramentas."

ABUSE_REPLY = (
    "Vamos manter a conversa respeitosa. "
    "Posso te ajudar com instrumentos, pedidos ou dúvidas da loja."
)


class AgentState(MessagesState):
    scope: str  # Scope value, set by the guard on every turn; a plain str checkpoints cleanly


type AgentGraph = CompiledStateGraph[AgentState, TurnContext, MessagesState, AgentState]


def bind_without_tool_calls(model: BaseChatModel, tools: Sequence[BaseTool]) -> Runnable:
    """Keep the tools defined (history may hold tool calls) but forbid new calls.

    Anthropic spells it `{"type": "none"}`; OpenAI and Gemini take `"none"`.
    """
    choice = {"type": "none"} if isinstance(model, ChatAnthropic) else "none"
    # Base signature types tool_choice as str; providers accept a dict as well.
    return model.bind_tools(tools, tool_choice=choice)  # pyright: ignore[reportArgumentType]


def _tool_failure(error: Exception) -> str:
    logger.error("tool raised", exc_info=error)
    return TOOL_FAILURE


def build_graph(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    classify: Callable[[Sequence[BaseMessage]], Scope],
    checkpointer: BaseCheckpointSaver[str],
    *,
    max_history_tokens: int = 3000,
) -> AgentGraph:
    with_tools = model.bind_tools(tools)
    without_calls = bind_without_tool_calls(model, tools)

    def guard(state: AgentState) -> dict[str, str]:
        return {"scope": classify(state["messages"]).value}

    def abuse_reply(state: AgentState) -> dict[str, list[BaseMessage]]:
        return {"messages": [AIMessage(ABUSE_REPLY)]}

    def agent(state: AgentState, runtime: Runtime[TurnContext]) -> dict[str, list[BaseMessage]]:
        ctx = runtime.context
        scope = Scope(state["scope"])
        messages = state["messages"]
        current = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
        turn = messages[current:]
        rounds = sum(isinstance(m, AIMessage) and bool(m.tool_calls) for m in turn)
        capped = rounds >= MAX_TOOL_ROUNDS
        notes = [NO_MORE_TOOLS] if capped else []
        if note := scope_note(scope):
            notes.append(note)
        # The current turn is never trimmed: only older history is, within what is left.
        budget = max(0, max_history_tokens - count_tokens_approximately(turn))
        history = trim_messages(
            messages[:current],
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=budget,
            start_on="human",
            end_on=("human", "ai", "tool"),
        )
        head = system_prompt(ctx.customer_name, ctx.today)
        prompt = [SystemMessage("\n\n".join([head, *notes])), *history, *turn]
        runner = with_tools if scope is Scope.LOJA and not capped else without_calls
        return {"messages": [runner.invoke(prompt)]}

    def route_scope(state: AgentState) -> str:
        return "abuse_reply" if state["scope"] == Scope.ABUSO else "agent"

    graph = StateGraph(AgentState, context_schema=TurnContext, input_schema=MessagesState)
    graph.add_node("guard", guard)
    graph.add_node("abuse_reply", abuse_reply)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=_tool_failure))
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", route_scope, ["abuse_reply", "agent"])
    graph.add_edge("abuse_reply", END)
    graph.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
