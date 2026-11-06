import re
from enum import StrEnum

from emporio.shared.text import fold
from emporio.support.domain.bubbles import MAX_BUBBLES, raw_bubbles

MAX_BUBBLE_CHARS = 280

# Stems over text folded and stripped of punctuation, so accents, case, hyphens and spacing
# do not matter ("Sinta-se à vontade" and "sinta se a vontade" are the same phrase).
_BANNED = re.compile(
    r"\bprezad[oa]s?\b|\ba disposicao\b|\bnao hesite\b"
    r"|\bfico feliz em (?:te )?ajudar\b|\bespero ter ajudado\b|\botima pergunta\b"
    r"|\bestou aqui (?:para|pra) (?:te )?ajudar\b|\bsinta se a vontade\b"
    r"|\bcomo posso (?:te )?ajudar hoje\b"
)
_PUNCTUATION = re.compile(r"[^\w\s]")

_MARKDOWN = re.compile(
    r"\*\*|__\w+__|^\s*(?:[-•*]|\d+[.)])\s|^\s*#{1,6}\s|(?<!\*)\*[^\s*][^*\n]*\*(?!\*)",
    re.MULTILINE,
)
_URL = re.compile(r"https?://\S+")
_TEXTSPEAK = re.compile(r"\b(?:vc|pq|blz|mano)\b")
_EM_DASH = chr(0x2014)
_EN_DASH = chr(0x2013)
_EMOJI = re.compile(f"[{chr(0x1F000)}-{chr(0x1FAFF)}{chr(0x2600)}-{chr(0x27BF)}{chr(0xFE0F)}]")
# en dash is fine inside a numeric range (9h-18h), a tell anywhere else
_STRAY_EN_DASH = re.compile(rf"(?<![\dh]){_EN_DASH}|{_EN_DASH}(?!\d)")
# A spaced hyphen between words is a dash in disguise; "9h-18h" and "9h - 18h" are ranges.
_SPACED_HYPHEN = re.compile(r"(?<=\w)(?<![\dh]) - (?=\w)|(?<=[\dh]) - (?=[^\W\d])")


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
    plain = " ".join(_PUNCTUATION.sub(" ", folded).split())
    bubbles = raw_bubbles(text)
    prose = _URL.sub("", text)
    prose_bubbles = raw_bubbles(prose)
    found = (
        (
            Tell.EM_DASH,
            _EM_DASH in text
            or bool(_STRAY_EN_DASH.search(text))
            or bool(_SPACED_HYPHEN.search(text)),
        ),
        (Tell.MARKDOWN, bool(_MARKDOWN.search(text))),
        (Tell.BANNED_PHRASE, bool(_BANNED.search(plain))),
        (Tell.TEXTSPEAK, bool(_TEXTSPEAK.search(folded))),
        (Tell.EMOJI, bool(_EMOJI.search(text))),
        (Tell.EXCLAMATIONS, text.count("!") > 1),
        (Tell.MULTIPLE_QUESTIONS, prose.count("?") > 1),
        (Tell.QUESTION_NOT_LAST, any("?" in b for b in prose_bubbles[:-1])),
        (Tell.TOO_MANY_BUBBLES, len(bubbles) > MAX_BUBBLES),
        (Tell.LONG_BUBBLE, any(len(b) > MAX_BUBBLE_CHARS for b in bubbles)),
    )
    return tuple(tell for tell, hit in found if hit)
