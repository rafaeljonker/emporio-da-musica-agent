"""Scope classifier: one structured-output call per turn, injected into the graph."""

import logging
from collections.abc import Callable, Sequence
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.prompt import guard_prompt

logger = logging.getLogger("emporio.support.guard")
MAX_PREVIOUS_CHARS = 500


class Label(BaseModel):
    label: Literal["loja", "acessorio", "fora_de_escopo", "abuso"]


def _text(message: BaseMessage) -> str:
    return message.text if message.text else ""


def make_classifier(model: BaseChatModel) -> Callable[[Sequence[BaseMessage]], Scope]:
    structured = model.with_structured_output(Label, method="json_schema")

    def classify(messages: Sequence[BaseMessage]) -> Scope:
        # A classifier failure must not abort the turn: fall back to the full store path.
        try:
            last = next(
                (
                    i
                    for i in range(len(messages) - 1, -1, -1)
                    if isinstance(messages[i], HumanMessage)
                ),
                None,
            )
            if last is None:
                return Scope.LOJA
            previous = next(
                (
                    _text(m)
                    for m in reversed(messages[:last])
                    if isinstance(m, AIMessage) and _text(m)
                ),
                "",
            )[:MAX_PREVIOUS_CHARS]
            prompt = f"Mensagem anterior do assistente: {previous or '(nenhuma)'}\n"
            prompt += f"Última mensagem do cliente: {_text(messages[last])}"
            answer = structured.invoke([SystemMessage(guard_prompt()), HumanMessage(prompt)])
            return Scope(Label.model_validate(answer).label)
        except Exception:
            logger.warning("guard fell back to loja", exc_info=True)
            return Scope.LOJA

    return classify
