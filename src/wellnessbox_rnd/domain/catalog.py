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

    return alias_index.get(_compact_catalog_text(normalized))


def normalize_catalog_text(value: str) -> str:
    collapsed = value.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(collapsed.split())


def _compact_catalog_text(value: str) -> str:
    return "".join(char for char in value if char.isalnum())
