"""pt-BR prompts. The system prompt is static first, dynamic suffix last, so prefix caching hits."""

from datetime import date
from functools import cache
from importlib.resources import files

from emporio.support.domain.scope import Scope

_PROMPTS = files("emporio.support.infrastructure.agent") / "prompts"
_STATIC = ("persona.md", "voice.md", "tools.md")

_SCOPE_NOTES = {
    Scope.ACESSORIO: (
        "A mensagem pede um acessório. Diga com leveza que a Empório trabalha só com "
        "instrumentos, sugira uma loja parceira de acessórios sem citar nome de loja, "
        "você não tem essa lista, e se ofereça pra ajudar se um instrumento entrar no plano."
    ),
    Scope.FORA_DE_ESCOPO: (
        "A mensagem não é sobre a loja. Diga com bom humor que disso você não entende, "
        "que seu negócio é instrumento, e puxe a conversa de volta pra música com uma pergunta "
        "só, no fim."
    ),
}


def _read(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8").strip()


@cache
def _static_prompt() -> str:
    return "\n\n".join(_read(name) for name in _STATIC)


def system_prompt(customer_name: str | None, today: date) -> str:
    customer = customer_name or "não identificado"
    tail = f"Cliente: {customer}\nData de referência de pedidos e trocas: {today:%d/%m/%Y}"
    return f"{_static_prompt()}\n\n{tail}"


@cache
def guard_prompt() -> str:
    return _read("guard.md")


def scope_note(scope: Scope) -> str:
    """Extra instruction for a tool-less reply; empty for scopes that need none."""
    return _SCOPE_NOTES.get(scope, "")
