import re

MAX_BUBBLES = 3


def raw_bubbles(text: str) -> tuple[str, ...]:
    parts = (p.strip() for p in re.split(r"\n\s*\n", text))
    return tuple(p for p in parts if p)


def split_bubbles(text: str) -> tuple[str, ...]:
    parts = raw_bubbles(text)
    if len(parts) <= MAX_BUBBLES:
        return parts
    return (*parts[: MAX_BUBBLES - 1], "\n\n".join(parts[MAX_BUBBLES - 1 :]))
