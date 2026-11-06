"""A model with no provider: `EMPORIO_FAKE_MODEL=1` swaps it in for e2e and local dev."""

from collections.abc import Sequence
from typing import override

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

FAILURE_MARKER = "[falha]"
REPLY = "Oi! Aqui é o modo de teste da Empório.\n\nVocê escreveu: {}"


class ScriptedFailure(RuntimeError):
    def __init__(self) -> None:
        super().__init__(f"scripted failure: the message contains {FAILURE_MARKER}")


class ScriptedChatModel(BaseChatModel):
    """Echoes the last customer message in two bubbles and never calls a tool."""

    @property
    @override
    def _llm_type(self) -> str:
        return "scripted"

    @override
    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | dict[str, str] | None = None,
        **kwargs: object,
    ) -> Runnable:
        return self

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        last = next((m.text for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        if FAILURE_MARKER in last:
            raise ScriptedFailure  # drives the e2e error state
        return ChatResult(generations=[ChatGeneration(message=AIMessage(REPLY.format(last)))])
