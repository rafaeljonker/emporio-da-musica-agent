from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from emporio.catalog.domain.product import Category, Product
from emporio.shared.money import Money
from emporio.shared.text import tokens

_STOPWORDS = frozenset(
    {"de", "da", "do", "e", "ate", "com", "para", "pra", "um", "uma"}
    | {"mai", "barato", "barata", "menor", "preco", "quero", "tem", "voce"}  # stemmed forms
)
_MIN_SCORE = 0.7
_EXACT_SCORE = 0.9
_TIER_GAP = 0.05
_MIN_PREFIX = 4


@dataclass(frozen=True, slots=True)
class Exact:
    product: Product


@dataclass(frozen=True, slots=True)
class Candidates:
    products: tuple[Product, ...]


@dataclass(frozen=True, slots=True)
class NoMatch:
    pass


type SearchResult = Exact | Candidates | NoMatch


@dataclass(frozen=True, slots=True)
class _Match:
    products: tuple[Product, ...]
    may_be_exact: bool


_NOTHING = _Match((), may_be_exact=False)


def search_products(
    products: Sequence[Product],
    categories: Sequence[Category],
    query: str,
    max_price: Money | None = None,
    include_unavailable: bool = False,
) -> SearchResult:
    words = _query_words(query)
    pool = tuple(p for p in products if max_price is None or p.price <= max_price)
    category_ids, rest = _match_categories(categories, words)
    if category_ids is None:
        found = _match_words(pool, words) if words else _NOTHING
    else:
        in_category = tuple(p for p in pool if p.category_id in category_ids)
        rest = tuple(w for w in rest if not w.isdigit())
        found = _match_words(in_category, rest) if rest else _Match(in_category, may_be_exact=True)
        if not found.products and words:
            # A category word may be part of a product name ("7 Cordas"): retry without the
            # filter, containment only, so a category query never fuzzes into another category.
            found = _Match(_contained(pool, words), may_be_exact=True)
    # Availability is applied after matching, so a hidden exact hit is not
    # replaced by a merely similar product (e.g. "SN-7C" must not become "SN-100").
    visible = tuple(p for p in found.products if include_unavailable or p.is_available)
    return _result(_Match(visible, found.may_be_exact))


def _query_words(query: str) -> tuple[str, ...]:
    raw = tokens(query)
    # "ate 1000" is a price, passed separately as max_price; never a model number.
    kept = (t for i, t in enumerate(raw) if not (t.isdigit() and i > 0 and raw[i - 1] == "ate"))
    return tuple(_digit_typos(t) for t in kept if t not in _STOPWORDS)


def _digit_typos(word: str) -> str:
    # In a model code, the letter "o" is almost always a mistyped zero ("gd 2O").
    return word.replace("o", "0") if any(c.isdigit() for c in word) else word


def _match_categories(
    categories: Sequence[Category], words: tuple[str, ...]
) -> tuple[frozenset[int] | None, tuple[str, ...]]:
    by_word = {w: frozenset(c.id for c in categories if w in tokens(c.name)) for w in words}
    matched = [ids for ids in by_word.values() if ids]
    if not matched:
        return None, words
    first, *others = matched
    return first.intersection(*others), tuple(w for w in words if not by_word[w])


def _match_words(pool: tuple[Product, ...], words: tuple[str, ...]) -> _Match:
    contained = _contained(pool, words)
    if contained:
        return _Match(contained, may_be_exact=True)
    scored = [(_fuzzy_score(words, tokens(p.name)), p) for p in pool]
    best = max((s for s, _ in scored), default=0.0)
    if best < _MIN_SCORE:
        return _NOTHING
    tier = tuple(p for s, p in scored if s >= best - _TIER_GAP)
    may_be_exact = best >= _EXACT_SCORE and all(
        _has_code(w, words, tokens(tier[0].name)) for w in words
    )
    return _Match(tier, may_be_exact=may_be_exact)


def _contained(pool: tuple[Product, ...], words: tuple[str, ...]) -> tuple[Product, ...]:
    return tuple(p for p in pool if all(_word_hits(w, tokens(p.name)) for w in words))


def _word_hits(word: str, name: tuple[str, ...]) -> bool:
    if word in name:
        return True
    is_code = any(c.isdigit() for c in word)
    return not is_code and len(word) >= _MIN_PREFIX and any(t.startswith(word) for t in name)


def _has_code(word: str, words: tuple[str, ...], name: tuple[str, ...]) -> bool:
    """A word with digits must appear in the name, alone or glued to the word before it."""
    if not any(c.isdigit() for c in word):
        return True
    i = words.index(word)
    return word in name or (i > 0 and words[i - 1] + word in name)


def _result(found: _Match) -> SearchResult:
    if not found.products:
        return NoMatch()
    if len(found.products) == 1 and found.may_be_exact:
        return Exact(found.products[0])
    return Candidates(tuple(sorted(found.products, key=lambda p: (p.price.amount, p.id))))


def _fuzzy_score(words: tuple[str, ...], name: tuple[str, ...]) -> float:
    needle = "".join(words)
    sizes = {max(1, len(words) + d) for d in (-1, 0, 1)}
    windows = ("".join(name[i : i + n]) for n in sizes for i in range(max(1, len(name) - n + 1)))
    return max((SequenceMatcher(None, needle, w).ratio() for w in windows), default=0.0)
