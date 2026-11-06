# Provider internals (private request builders, loosely typed constructors) are probed on purpose.
# pyright: reportArgumentType=false, reportCallIssue=false, reportPrivateUsage=false
from collections.abc import Callable

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableBinding
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from emporio.support.infrastructure.agent.graph import bind_without_tool_calls


@tool
def ping(x: int) -> int:
    """Return x."""
    return x


def _openai() -> BaseChatModel:
    return ChatOpenAI(model="m", api_key="k", base_url="http://localhost:1")


def _gemini() -> BaseChatModel:
    return ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key="k")


def _anthropic() -> BaseChatModel:
    return ChatAnthropic(model="claude-haiku-5-5", api_key="k")


def _openai_choice(model: BaseChatModel, kwargs: dict[str, object]) -> object:
    assert isinstance(model, ChatOpenAI)
    return model._get_request_payload([HumanMessage("hi")], **kwargs)["tool_choice"]


def _anthropic_choice(model: BaseChatModel, kwargs: dict[str, object]) -> object:
    assert isinstance(model, ChatAnthropic)
    return model._get_request_payload([HumanMessage("hi")], **kwargs)["tool_choice"]


def _gemini_choice(model: BaseChatModel, kwargs: dict[str, object]) -> object:
    assert isinstance(model, ChatGoogleGenerativeAI)
    request = model._prepare_request([HumanMessage("hi")], **kwargs)
    mode = request["config"].tool_config.function_calling_config.mode
    return str(mode).rsplit(".", 1)[-1]


@pytest.mark.parametrize(
    ("make", "choice", "expected"),
    [
        (_openai, _openai_choice, "none"),
        (_anthropic, _anthropic_choice, {"type": "none"}),
        (_gemini, _gemini_choice, "NONE"),
    ],
)
def test_provider_accepts_tool_choice_none(
    make: Callable[[], BaseChatModel],
    choice: Callable[[BaseChatModel, dict[str, object]], object],
    expected: object,
) -> None:
    model = make()
    bound = bind_without_tool_calls(model, [ping])
    assert isinstance(bound, RunnableBinding)
    assert choice(model, bound.kwargs) == expected
