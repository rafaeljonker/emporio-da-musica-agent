"""Paraphrase-tolerant verifier for the agent golden cases. Pure functions, no IO.

Both the reply and every expected token are normalized the same way (accents, case, "R$",
thousands dots, ",00"), so "R$ 2.199,00", "2199 reais" and "R$2.199" all match the amount
"R$ 2.199". A token is a phrase, a "@group" of synonyms, or a "{fact}" placeholder that
`expand` fills from facts derived at test time. Lessons from the spike: "9x", "9 parcelas" and
"nove vezes" are one answer; "descontinuado" and "saiu de linha" are one answer.
"""

# ponytail: regex heuristics with a known ceiling. A wrong verdict is audited by reading the
# failure transcripts in the report; the upgrade path is an LLM judge (report-only, not gating).

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from emporio.shared.errors import DomainError
from emporio.shared.text import fold

type Facts = Mapping[str, str | tuple[str, ...]]


class UnknownGroup(DomainError):
    def __init__(self, name: str) -> None:
        super().__init__(f"unknown synonym group @{name}")


_NUMBER_WORDS = ("zero", "um", "dois", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove")
_NUMBER_WORDS += ("dez", "onze", "doze")

# Regexes over normalized text (lowercase, no accents).
_NOT_DISCONTINUED = (
    r"(?!.*(descontinu|saiu de linha|fora de linha|nao (esta|temos|tem|tenho|ha|trabalhamos)"
    r"|indisponivel|esgotad|nao vende(mos)? mais))"
)
_NOT_RETURN_NO = (
    r"(?!.*(fora do prazo|(?<!nao )(passou|venceu|expirou)"
    r"|nao (esta|ta) (mais )?(no|dentro do) prazo"
    r"|nao (da|e possivel|consigo|posso)( mais)? (pra |para )?(fazer a )?devol))"
)
_NOT_CLOSED = r"(?!.*(fechad|nao (estamos|tamo|to|esta|ta) (abert|funcionando)|nao abrimos))"

GROUPS: dict[str, str] = {
    "discontinued": (
        r"descontinu|saiu de linha|fora de linha|nao esta mais disponivel|nao faz mais parte"
        r"|nao (temos|tem|trabalhamos com) mais|indisponivel|esgotad"
        r"|nao (esta|ta) mais no catalogo|nao vende(mos)? mais"
    ),
    # A reply that also says "saiu de linha" or "nao temos" never claims to have it.
    "has_it": (
        rf"^{_NOT_DISCONTINUED}.*(\b(temos|tem|tenho) sim\b|temos em estoque|esta disponivel)"
    ),
    "regret_7": r"\b(7|sete) dias",
    "asks_identity": r"numero do pedido|e-?mail|telefone|cpf",
    "instruments": r"instrument",
    "declines_accessory": (
        r"nao (vende(\(mos\)|mos)?|trabalhamos com|temos|tem) (\w+ )?"
        r"(encordoamento|acessori|corda|cabo|palheta|pedal|amplificador|case)"
        r"|(?<!nao )(?<!nao temos )(?<!nao tem )(so|apenas|somente) "
        r"(trabalhamos |vendemos |temos )?(com )?instrumentos"
    ),
    "asks_model": (
        r"qual (modelo|deles|desses|dos)|que modelo|algum modelo|de qual"
        r"|qual (voce|vc) (procura|quer|prefere)"
    ),
    "store_topic": r"instrument|loja|violao|guitarra|musica|emporio",
    "recommends_movie": r"recomend\w* (o|um) filme|assista|assiste|que tal assistir",
    "return_yes": (
        rf"^{_NOT_RETURN_NO}.*(pode devolver|da pra devolver|consegue devolver|dentro do prazo"
        r"|esta no prazo|tem direito|ainda da)"
    ),
    "return_no": (
        r"fora do prazo|nao (esta|ta) (mais )?(no|dentro do) prazo"
        r"|prazo\b.{0,40}\b(?<!nao )(passou|acabou|venceu|expirou|encerrou|terminou)"
        r"|(?<!nao )(passou|acabou|venceu|expirou)\b.{0,15}\bprazo"
        r"|nao (da|e possivel|consigo|posso)( mais)? (pra |para )?(fazer a )?devol"
        r"|nao da mais"
    ),
    # An open store never also says it is closed or "not open": "fechado, amanha estamos abertos".
    "store_open": (
        rf"^{_NOT_CLOSED}.*((estamos|tamo|to|esta|ta|a gente esta) (abert|funcionando)"
        r"|funcionando agora)"
    ),
    "store_closed": r"fechad|nao (estamos|tamo|to|esta|ta) (abert|funcionando)|nao abrimos",
    "status_delivered": (r"(?<!nao )(?<!nao foi )(?<!nao esta )\bentregue\b|(?<!nao )chegou"),
    "claim_delivered": (
        r"(?<!nao )(?<!confirmar se )(?<!saber se )(?<!dizer se )foi entregue"
        r"|entregue em|ja (foi )?entregue|(?<!nao )chegou"
    ),
    "status_shipped": r"enviad|a caminho|transito|postad|despachad",
    "status_confirmed": r"confirmad|separa|preparand",
    "status_pending": r"pendente|aguardando|pagamento",
    "status_cancelled": r"cancelad",
    "legal_warranty": (
        r"^(?!.*garantia\b.{0,30}\b(acabou|expirou|venceu|passou|encerrou|terminou))"
        r".*(garantia legal|90 dias|noventa dias|\bcdc\b|codigo de defesa)"
    ),
}


def _installments(n: int) -> str:
    word = _NUMBER_WORDS[n] if n < len(_NUMBER_WORDS) else str(n)
    return rf"(?<!\d){n}\s?x\b|(?<!\d){n} (vezes|parcelas|x)\b|\b{word} (vezes|parcelas)"


def normalize(text: str) -> str:
    folded = re.sub(r"r\$\s*", "", fold(text))
    folded = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", folded)  # thousands dots
    return re.sub(r"(?<=\d),00(?!\d)", "", folded)


def _group(name: str) -> str:
    if name.startswith("installments_") and name.removeprefix("installments_").isdigit():
        return _installments(int(name.removeprefix("installments_")))
    if name not in GROUPS:
        raise UnknownGroup(name)
    return GROUPS[name]


def _pattern(token: str) -> str:
    if token.startswith("@"):
        return _group(token[1:])
    literal = normalize(token)
    pattern = re.escape(literal)
    if literal[:1].isdigit():
        pattern = r"(?<!\d)" + pattern
    if literal[-1:].isdigit():
        pattern += r"(?!\d|[.,]\d)"
    return pattern


def matches(token: str, normalized_text: str) -> bool:
    return re.search(_pattern(token), normalized_text) is not None


def expand(token: str, facts: Facts) -> tuple[str, ...]:
    """Fill `{fact}` placeholders; a token that is exactly one list fact becomes its items."""
    whole = re.fullmatch(r"\{(\w+)\}", token)
    if whole and isinstance(facts[whole.group(1)], tuple):
        return tuple(facts[whole.group(1)])
    return (token.format_map({k: v for k, v in facts.items() if isinstance(v, str)}),)


@dataclass(frozen=True)
class Expect:
    expect_tools: tuple[str, ...] = ()
    all_of: tuple[str, ...] = ()
    any_of: tuple[str, ...] | None = None  # () means "required but no candidate": always fails
    none_of: tuple[str, ...] = ()
    ask: bool = False


@dataclass(frozen=True)
class Verdict:
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def verify(expect: Expect, bubbles: Sequence[str], tools_used: Sequence[str]) -> Verdict:
    # `ask` looks at the LAST bubble only: the voice guide puts the question there, and an
    # earlier question is already an AI tell caught by the detector.
    text = normalize("\n".join(bubbles))
    failures: list[str] = []
    missing = [t for t in expect.expect_tools if t not in tools_used]
    if missing:
        failures.append(f"tools not called: {', '.join(missing)}")
    failures += [f"missing: {t}" for t in expect.all_of if not matches(t, text)]
    if expect.any_of is not None and not any(matches(t, text) for t in expect.any_of):
        failures.append(f"none of: {', '.join(expect.any_of) or '(no candidates derived)'}")
    failures += [f"forbidden: {t}" for t in expect.none_of if matches(t, text)]
    if expect.ask and not (bubbles and bubbles[-1].strip().endswith("?")):
        failures.append("last bubble is not a question")
    return Verdict(tuple(failures))
