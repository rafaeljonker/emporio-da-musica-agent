import re
import unicodedata


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(bare.casefold().split())


_LONG_PLURALS = (("ores", "or"), ("ais", "al"), ("eis", "el"))


def stem(word: str) -> str:
    if word == "oboes":
        return "oboe"
    if word.endswith(("oes", "aes", "aos")):
        return word[:-3] + "ao"
    if len(word) > 5:
        for plural, singular in _LONG_PLURALS:
            if word.endswith(plural):
                return word[: -len(plural)] + singular
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def tokens(text: str) -> tuple[str, ...]:
    return tuple(stem(t) for t in re.split(r"[^a-z0-9]+", fold(text)) if t)
