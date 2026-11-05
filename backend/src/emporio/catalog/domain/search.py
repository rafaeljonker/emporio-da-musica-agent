from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import pairwise

from emporio.catalog.domain.product import Category, Product
from emporio.shared.money import Money
from emporio.shared.text import stem, tokens

_STOPWORDS = frozenset(
    {"de", "da", "do", "e", "ate", "com", "para", "pra", "um", "uma"}
    | {"mai", "barato", "barata", "menor", "preco", "quero", "tem", "voce"}  # stemmed forms
)
_MIN_SCORE = 0.7
_EXACT_SCORE = 0.9
_TIER_GAP = 0.05
_MIN_PREFIX = 4
_MIN_PRICE_DIGITS = 3


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
    name_ids: frozenset[int]  # matched by name; these win over description-only matches


_NOTHING = _Match((), frozenset())


def search_products(
    products: Sequence[Product],
    categories: Sequence[Category],
    query: str,
    max_price: Money | None = None,
    include_unavailable: bool = False,
) -> SearchResult:
    words = _query_words(query)
    pool = tuple(p for p in products if max_price is None or p.price <= max_price)
    stocked = [c for c in categories if any(p.category_id == c.id for p in pool)]
    matched, rest = _match_categories(stocked, words)
    if not matched:
        found = _match_words(pool, words) if words else _NOTHING
    else:
        ids = frozenset(c.id for c in matched)
        in_category = tuple(p for p in pool if p.category_id in ids)
        # A word only the category itself describes ("teclado digital") adds nothing; one
        # that also names products ("ukulele soprano") still narrows.
        described = _terms(" ".join(c.name + " " + c.description for c in matched))
        rest = tuple(
            w
            for w in rest
            if not _is_price(w)
            and not (_hits(w, (), described) and not _contained(in_category, (w,)).products)
        )
        if rest:
            found = _match_words(in_category, rest)
        else:
            found = _Match(in_category, frozenset(p.id for p in in_category))
        if not found.products:
            # A category word may be part of a product name ("7 Cordas"): retry without the
            # filter, containment only, so a category query never fuzzes into another category.
            found = _contained(pool, words)
    # Availability is applied after matching, so a hidden exact hit is not
    # replaced by a merely similar product (e.g. "SN-7C" must not become "SN-100").
    visible = tuple(p for p in found.products if include_unavailable or p.is_available)
    return _result(_Match(visible, found.name_ids))


def _query_words(query: str) -> tuple[str, ...]:
    raw = tokens(query)
    # "ate 1000" is a price, passed separately as max_price; never a model number.
    kept = (t for i, t in enumerate(raw) if not (t.isdigit() and i > 0 and raw[i - 1] == "ate"))
    return tuple(_digit_typos(t) for t in kept if t not in _STOPWORDS)


def _has_digit(word: str) -> bool:
    return any(c.isdigit() for c in word)


def _is_price(word: str) -> bool:
    return word.isdigit() and len(word) >= _MIN_PRICE_DIGITS


def _digit_typos(word: str) -> str:
    # In a model code, the letter "o" is almost always a mistyped zero ("gd 2O").
    return word.replace("o", "0") if _has_digit(word) else word


def _terms(text: str) -> tuple[str, ...]:
    """Tokens plus adjacent pairs glued: "D-28" also reads "d28", "KA-15S" also "ka15"."""
    words = tokens(text)
    glued = tuple(a + b for a, b in pairwise(words))
    return words + glued + tuple(stem(g) for g in glued)


def _match_categories(
    categories: Sequence[Category], words: tuple[str, ...]
) -> tuple[tuple[Category, ...], tuple[str, ...]]:
    by_word = {w: tuple(c for c in categories if w in tokens(c.name)) for w in words}
    matched = tuple({c.id: c for cats in by_word.values() for c in cats}.values())
    return matched, tuple(w for w in words if not by_word[w])


def _match_words(pool: tuple[Product, ...], words: tuple[str, ...]) -> _Match:
    contained = _contained(pool, words)
    if contained.products:
        return contained
    return _fuzzy(pool, words)


def _contained(pool: tuple[Product, ...], words: tuple[str, ...]) -> _Match:
    # Name or description ("jazz bass" finds the bass described as a Jazz Bass), but only
    # a product whose NAME holds every word may be Exact: descriptions disagree with names.
    found = tuple(p for p in pool if _all_hit(words, _terms(p.name + " " + p.description)))
    return _Match(found, frozenset(p.id for p in found if _all_hit(words, _terms(p.name))))


def _all_hit(words: tuple[str, ...], terms: tuple[str, ...]) -> bool:
    return all(
        _hits(w, words[i - 1 : i] + words[i + 1 : i + 2], terms) for i, w in enumerate(words)
    )


def _hits(word: str, neighbours: tuple[str, ...], terms: tuple[str, ...]) -> bool:
    if word in terms:
        return True
    # A split model code: "gd 20" against "gd20".
    if any(n + word in terms or word + n in terms for n in neighbours):
        return True
    return (
        not _has_digit(word) and len(word) >= _MIN_PREFIX and any(t.startswith(word) for t in terms)
    )


def _fuzzy(pool: tuple[Product, ...], words: tuple[str, ...]) -> _Match:
    # Numbers are never fuzzed: "1000" must not become "100".
    letters = tuple(w for w in words if not _has_digit(w))
    if not letters:
        return _NOTHING
    scored = [(_fuzzy_score(letters, tokens(p.name)), p) for p in pool]
    best = max((s for s, _ in scored), default=0.0)
    if best < _MIN_SCORE:
        return _NOTHING
    tier = tuple(p for s, p in scored if s >= best - _TIER_GAP)
    name = _terms(tier[0].name)
    neighbours = [words[i - 1 : i] + words[i + 1 : i + 2] for i in range(len(words))]
    codes_found = all(
        _hits(w, near, name) for w, near in zip(words, neighbours, strict=True) if _has_digit(w)
    )
    exact = len(tier) == 1 and best >= _EXACT_SCORE and codes_found
    return _Match(tier, frozenset({tier[0].id}) if exact else frozenset())


def _result(found: _Match) -> SearchResult:
    by_name = tuple(p for p in found.products if p.id in found.name_ids)
    best = by_name or found.products
    if not best:
        return NoMatch()
    if len(by_name) == 1:
        return Exact(by_name[0])
    return Candidates(tuple(sorted(best, key=lambda p: (p.price.amount, p.id))))


def _fuzzy_score(words: tuple[str, ...], name: tuple[str, ...]) -> float:
    needle = "".join(words)
    sizes = {max(1, len(words) + d) for d in (-1, 0, 1)}
    windows = ("".join(name[i : i + n]) for n in sizes for i in range(max(1, len(name) - n + 1)))
    return max((SequenceMatcher(None, needle, w).ratio() for w in windows), default=0.0)
