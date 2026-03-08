import json
from functools import lru_cache
from pathlib import Path

from wellnessbox_rnd.domain.models import IngredientCatalogItem, SafetyRuleSet


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache
def load_ingredient_catalog() -> list[IngredientCatalogItem]:
    path = repo_root() / "data" / "catalog" / "ingredients.json"
    raw_items = json.loads(path.read_text(encoding="utf-8"))
    return [IngredientCatalogItem.model_validate(item) for item in raw_items]


@lru_cache
def load_safety_rules() -> SafetyRuleSet:
    path = repo_root() / "data" / "rules" / "safety_rules.json"
    raw_rules = json.loads(path.read_text(encoding="utf-8"))
    return SafetyRuleSet.model_validate(raw_rules)

