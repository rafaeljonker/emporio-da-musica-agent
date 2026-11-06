import re
from collections.abc import Sequence

MAX_BUBBLES = 3
MAX_TOTAL_DELAY_MS = 3000


CHANNEL_BLOCK = re.compile(r"<\|channel>.*?<channel\|>", re.DOTALL)
CHANNEL_TOKEN = re.compile(r"<\|channel>|<channel\|>")
# A single closing "." per line, never "..." (WhatsApp messages rarely end in a period).
FINAL_PERIOD = re.compile(r"(?<!\.)\.[ \t]*$", re.MULTILINE)


def strip_channel_markup(text: str) -> str:
    """Gemma 4 thinking-channel blocks (empty or not) and stray channel tokens, removed."""
    return CHANNEL_TOKEN.sub("", CHANNEL_BLOCK.sub("", text)).strip()


def raw_bubbles(text: str) -> tuple[str, ...]:
    text = strip_channel_markup(text)
    parts = (FINAL_PERIOD.sub("", p.strip()) for p in re.split(r"\n\s*\n", text))
    return tuple(p for p in parts if p)


def split_bubbles(text: str) -> tuple[str, ...]:
    """At most MAX_BUBBLES, merging the shortest neighbours line by line; no word is dropped."""
    parts = list(raw_bubbles(text))
    while len(parts) > MAX_BUBBLES:
        i = min(range(len(parts) - 1), key=lambda j: len(parts[j]) + len(parts[j + 1]))
        parts[i : i + 2] = [f"{parts[i]}\n{parts[i + 1]}"]
    return tuple(parts)


def pace_bubbles(bubbles: Sequence[str]) -> tuple[int, ...]:
    """Delay before each bubble: typing time by length, clamped, 3 s overall."""
    delays: list[int] = []
    total = 0
    for i, text in enumerate(bubbles):
        delay = (
            0 if i == 0 else min(max(400 + 22 * len(text), 700), 2400, MAX_TOTAL_DELAY_MS - total)
        )
        total += delay
        delays.append(delay)
    return tuple(delays)
