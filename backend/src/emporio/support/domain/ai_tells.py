import re
from enum import StrEnum

from emporio.shared.text import fold
from emporio.support.domain.bubbles import MAX_BUBBLES, raw_bubbles

MAX_BUBBLE_CHARS = 280

_BANNED = (
    "fico feliz em ajudar",
    "ótima pergunta",
    "espero ter ajudado",
    "não hesite em",
    "estou aqui para ajudar",
    "sinta-se à vontade",
    "qualquer dúvida estou à disposição",
    "como posso te ajudar hoje?",
    "prezado(a)",
)
_BANNED_FOLDED = tuple(fold(p) for p in _BANNED)

_MARKDOWN = re.compile(r"\*\*|__\w+__|^\s*(?:[-•*]|\d+[.)])\s|^\s*#{1,6}\s", re.MULTILINE)
_URL = re.compile(r"https?://\S+")
_TEXTSPEAK = re.compile(r"\b(?:vc|pq|blz)\b")
_EM_DASH = chr(0x2014)
_EN_DASH = chr(0x2013)
_EMOJI = re.compile(f"[{chr(0x1F000)}-{chr(0x1FAFF)}{chr(0x2600)}-{chr(0x27BF)}{chr(0xFE0F)}]")
# en dash is fine inside a numeric range (9h-18h), a tell anywhere else
_STRAY_EN_DASH = re.compile(rf"(?<![\dh]){_EN_DASH}|{_EN_DASH}(?!\d)")


class Tell(StrEnum):
    EM_DASH = "em_dash"
    MARKDOWN = "markdown"
    BANNED_PHRASE = "banned_phrase"
    TEXTSPEAK = "textspeak"
    EMOJI = "emoji"
    EXCLAMATIONS = "exclamations"
    MULTIPLE_QUESTIONS = "multiple_questions"
    QUESTION_NOT_LAST = "question_not_last"
    TOO_MANY_BUBBLES = "too_many_bubbles"
    LONG_BUBBLE = "long_bubble"


def ai_tells(text: str) -> tuple[Tell, ...]:
    folded = fold(text)
    bubbles = raw_bubbles(text)
    prose = _URL.sub("", text)
    prose_bubbles = raw_bubbles(prose)
    found = (
        (Tell.EM_DASH, _EM_DASH in text or bool(_STRAY_EN_DASH.search(text))),
        (Tell.MARKDOWN, bool(_MARKDOWN.search(text))),
        (Tell.BANNED_PHRASE, any(p in folded for p in _BANNED_FOLDED)),
        (Tell.TEXTSPEAK, bool(_TEXTSPEAK.search(folded))),
        (Tell.EMOJI, bool(_EMOJI.search(text))),
        (Tell.EXCLAMATIONS, text.count("!") > 1),
        (Tell.MULTIPLE_QUESTIONS, prose.count("?") > 1),
        (Tell.QUESTION_NOT_LAST, any("?" in b for b in prose_bubbles[:-1])),
        (Tell.TOO_MANY_BUBBLES, len(bubbles) > MAX_BUBBLES),
        (Tell.LONG_BUBBLE, any(len(b) > MAX_BUBBLE_CHARS for b in bubbles)),
    )
    return tuple(tell for tell, hit in found if hit)
