import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from emporio.support.domain.bubbles import split_bubbles
from emporio.support.infrastructure.llm.scripted import ScriptedChatModel


def test_scripted_model_echoes_in_two_bubbles() -> None:
    model = ScriptedChatModel().bind_tools([])
    answer = model.invoke([SystemMessage("prompt"), HumanMessage("antes"), HumanMessage("Oi")])
    assert split_bubbles(answer.text) == (
        "Oi! Aqui é o modo de teste da Empório.",
        "Você escreveu: Oi",
    )
    assert not answer.tool_calls


def test_scripted_model_fails_on_marker() -> None:
    with pytest.raises(RuntimeError):
        ScriptedChatModel().invoke([HumanMessage("isso vai dar [falha]")])
