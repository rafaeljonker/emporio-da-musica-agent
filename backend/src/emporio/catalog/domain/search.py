from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from emporio.catalog.domain.product import Category, Product
from emporio.shared.money import Money
from emporio.shared.text import tokens

_STOPWORDS = frozenset({"de", "da", "do", "e", "ate", "com", "para", "pra", "um", "uma"})
_MIN_SCORE = 0.6
_TIER_GAP = 0.05


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


def search_products(
    products: Sequence[Product],
    categories: Sequence[Category],
    query: str,
    max_price: Money | None = None,
    include_unavailable: bool = False,
) -> SearchResult:
    words = tuple(t for t in tokens(query) if t not in _STOPWORDS)
    pool = tuple(p for p in products if max_price is None or p.price <= max_price)
    category_ids, rest = _match_categories(categories, words)
    found: tuple[Product, ...] = ()
    if category_ids:
        in_category = tuple(p for p in pool if p.category_id in category_ids)
        found = _match_words(in_category, rest) if rest else in_category
    if not found and words:
        # A category word may be part of a product name ("7 Cordas"): retry without the filter.
        found = _match_words(pool, words)
    # Availability is applied after matching, so a hidden exact hit is not
    # replaced by a merely similar product (e.g. "SN-7C" must not become "SN-100").
    return _result(tuple(p for p in found if include_unavailable or p.is_available))


def _match_categories(
    categories: Sequence[Category], words: tuple[str, ...]
) -> tuple[frozenset[int], tuple[str, ...]]:
    by_word = {w: frozenset(c.id for c in categories if w in tokens(c.name)) for w in words}
    matched = [ids for ids in by_word.values() if ids]
    if not matched:
        return frozenset(), words
    first, *others = matched
    narrowed = first.intersection(*others) or first.union(*others)
    return narrowed, tuple(w for w in words if not by_word[w])


def _match_words(pool: tuple[Product, ...], words: tuple[str, ...]) -> tuple[Product, ...]:
    contained = tuple(p for p in pool if set(words) <= set(tokens(p.name)))
    if contained:
        return contained
    scored = [(_fuzzy_score(words, tokens(p.name)), p) for p in pool]
    passing = [(s, p) for s, p in scored if s >= _MIN_SCORE]
    if not passing:
        return ()
    best = max(s for s, _ in passing)
    return tuple(p for s, p in passing if s >= best - _TIER_GAP)


def _result(found: tuple[Product, ...]) -> SearchResult:
    if not found:
        return NoMatch()
    if len(found) == 1:
        return Exact(found[0])
    return Candidates(tuple(sorted(found, key=lambda p: (p.price.amount, p.id))))


def _fuzzy_score(words: tuple[str, ...], name: tuple[str, ...]) -> float:
    needle = "".join(words)
    sizes = {max(1, len(words) + d) for d in (-1, 0, 1)}
    windows = ("".join(name[i : i + n]) for n in sizes for i in range(max(1, len(name) - n + 1)))
    return max((SequenceMatcher(None, needle, w).ratio() for w in windows), default=0.0)
