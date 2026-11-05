import re
import unicodedata


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(bare.casefold().split())


def stem(token: str) -> str:
    if token.endswith(("oes", "aes", "aos")):
        return token[:-3] + "ao"
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def tokens(text: str) -> tuple[str, ...]:
    return tuple(stem(t) for t in re.split(r"[^a-z0-9]+", fold(text)) if t)
