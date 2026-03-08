from wellnessbox_rnd.domain.loaders import load_ingredient_catalog
from wellnessbox_rnd.domain.models import IngredientCatalogItem


def list_catalog_items() -> list[IngredientCatalogItem]:
    return load_ingredient_catalog()


def get_catalog_index() -> dict[str, IngredientCatalogItem]:
    return {item.key: item for item in load_ingredient_catalog()}

