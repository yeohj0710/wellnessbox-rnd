from functools import lru_cache

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog
from wellnessbox_rnd.domain.models import IngredientCatalogItem


def list_catalog_items() -> list[IngredientCatalogItem]:
    return load_ingredient_catalog()


def get_catalog_index() -> dict[str, IngredientCatalogItem]:
    return {item.key: item for item in load_ingredient_catalog()}


@lru_cache
def get_catalog_alias_index() -> dict[str, str]:
    alias_index: dict[str, str] = {}
    for item in load_ingredient_catalog():
        for term in [item.key, item.display_name, *item.aliases]:
            normalized = normalize_catalog_text(term)
            if not normalized:
                continue
            alias_index[normalized] = item.key
            alias_index[_compact_catalog_text(normalized)] = item.key
    return alias_index


def canonicalize_catalog_term(value: str) -> str | None:
    normalized = normalize_catalog_text(value)
    if not normalized:
        return None

    alias_index = get_catalog_alias_index()
    if normalized in alias_index:
        return alias_index[normalized]

    compact = _compact_catalog_text(normalized)
    if compact in alias_index:
        return alias_index[compact]

    return _fuzzy_catalog_title_match(normalized, compact)


def normalize_catalog_text(value: str) -> str:
    collapsed = value.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(collapsed.split())


def _compact_catalog_text(value: str) -> str:
    return "".join(char for char in value if char.isalnum())


@lru_cache
def _catalog_term_candidates() -> list[tuple[str, str, str, frozenset[str]]]:
    candidates: list[tuple[str, str, str, frozenset[str]]] = []
    seen: set[tuple[str, str]] = set()
    for item in load_ingredient_catalog():
        for term in [item.key, item.display_name, *item.aliases]:
            normalized = normalize_catalog_text(term)
            if not normalized:
                continue
            key = (item.key, normalized)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                (
                    item.key,
                    normalized,
                    _compact_catalog_text(normalized),
                    frozenset(_meaningful_catalog_tokens(normalized)),
                )
            )
    return candidates


def _fuzzy_catalog_title_match(normalized_value: str, compact_value: str) -> str | None:
    scored_matches: list[tuple[tuple[int, int, int], str]] = []
    value_tokens = frozenset(_meaningful_catalog_tokens(normalized_value))

    for item_key, normalized_term, compact_term, term_tokens in _catalog_term_candidates():
        score = _catalog_match_score(
            normalized_value=normalized_value,
            compact_value=compact_value,
            value_tokens=value_tokens,
            normalized_term=normalized_term,
            compact_term=compact_term,
            term_tokens=term_tokens,
        )
        if score is not None:
            scored_matches.append((score, item_key))

    if not scored_matches:
        return None

    scored_matches.sort(reverse=True)
    best_score, best_key = scored_matches[0]
    conflicting_keys = {
        item_key
        for score, item_key in scored_matches
        if score == best_score
    }
    if len(conflicting_keys) > 1:
        return None
    return best_key


def _catalog_match_score(
    *,
    normalized_value: str,
    compact_value: str,
    value_tokens: frozenset[str],
    normalized_term: str,
    compact_term: str,
    term_tokens: frozenset[str],
) -> tuple[int, int, int] | None:
    if (
        len(normalized_term) >= 6
        and _contains_catalog_token_sequence(
            _catalog_sequence_tokens(normalized_value),
            _catalog_sequence_tokens(normalized_term),
        )
    ):
        return (3, len(term_tokens), len(compact_term))

    if (
        compact_term
        and compact_term in compact_value
        and len(compact_term) >= 6
        and (len(term_tokens) <= 1 or term_tokens.issubset(value_tokens))
    ):
        return (2, len(term_tokens), len(compact_term))

    if term_tokens and term_tokens.issubset(value_tokens):
        return (1, len(term_tokens), len(compact_term))

    return None


def _catalog_sequence_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for raw_token in normalize_catalog_text(value).split():
        cleaned = "".join(char for char in raw_token if char.isalnum())
        if not cleaned or cleaned.isdigit():
            continue
        tokens.append(cleaned)
    return tuple(tokens)


def _contains_catalog_token_sequence(
    value_tokens: tuple[str, ...], term_tokens: tuple[str, ...]
) -> bool:
    if not value_tokens or not term_tokens or len(term_tokens) > len(value_tokens):
        return False

    term_window = len(term_tokens)
    for index in range(len(value_tokens) - term_window + 1):
        if value_tokens[index : index + term_window] == term_tokens:
            return True
    return False


def _meaningful_catalog_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in normalize_catalog_text(value).split():
        cleaned = "".join(char for char in raw_token if char.isalnum())
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        tokens.append(cleaned)
        digit_stripped = "".join(char for char in cleaned if not char.isdigit())
        if digit_stripped and digit_stripped != cleaned:
            tokens.append(digit_stripped)
    return tokens
