from collections.abc import Sequence
from typing import override

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field


class FakeToolCallingModel(GenericFakeChatModel):
    """Scripted model that records what it was sent. Build one per test."""

    seen: list[list[BaseMessage]] = Field(default_factory=list)
    bind_calls: int = 0

    def bind_tools(self, tools: Sequence[BaseTool], **kwargs: object) -> Runnable:  # type: ignore[override]  # base has a wider signature
        self.bind_calls += 1
        return self

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self.seen.append(list(messages))
        return super()._generate(messages, stop, run_manager, **kwargs)
