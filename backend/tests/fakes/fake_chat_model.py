from collections.abc import Sequence
from typing import override

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from pydantic import Field

type Choice = str | dict[str, str] | None


class FakeToolCallingModel(GenericFakeChatModel):
    """Scripted model that records what it was sent. Build one per test."""

    seen: list[list[BaseMessage]] = Field(default_factory=list)
    tool_choice: Choice = None
    seen_choice: list[Choice] = Field(default_factory=list)

    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: Choice = None,
        **kwargs: object,
    ) -> Runnable:  # type: ignore[override]  # base has a wider signature
        # Shallow copy: shares the script iterator and the `seen` lists, keeps the choice.
        return self.model_copy(update={"tool_choice": tool_choice})

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self.seen.append(list(messages))
        self.seen_choice.append(self.tool_choice)
        return super()._generate(messages, stop, run_manager, **kwargs)
