import re
from collections.abc import Sequence

MAX_BUBBLES = 3
MAX_TOTAL_DELAY_MS = 3000


def raw_bubbles(text: str) -> tuple[str, ...]:
    parts = (p.strip() for p in re.split(r"\n\s*\n", text))
    return tuple(p for p in parts if p)


def split_bubbles(text: str) -> tuple[str, ...]:
    parts = raw_bubbles(text)
    if len(parts) <= MAX_BUBBLES:
        return parts
    return (*parts[: MAX_BUBBLES - 1], "\n\n".join(parts[MAX_BUBBLES - 1 :]))


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
