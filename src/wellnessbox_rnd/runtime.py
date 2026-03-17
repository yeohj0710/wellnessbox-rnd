from pathlib import Path

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog, load_safety_rules, repo_root
from wellnessbox_rnd.knowledge.runtime_db import load_runtime_knowledge_db


def validate_runtime_readiness() -> dict[str, int | str]:
    root = repo_root()
    catalog_path = root / "data" / "catalog" / "ingredients.json"
    safety_rules_path = root / "data" / "rules" / "safety_rules.json"
    runtime_knowledge_path = root / "data" / "knowledge" / "runtime_knowledge_db_v1.json"
    reference_knowledge_path = root / "data" / "knowledge" / "reference_knowledge_base_v1.json"

    missing_paths = [
        str(path)
        for path in (catalog_path, safety_rules_path)
        if not path.exists()
    ]
    if not runtime_knowledge_path.exists() and not reference_knowledge_path.exists():
        missing_paths.append(str(runtime_knowledge_path))
        missing_paths.append(str(reference_knowledge_path))
    if missing_paths:
        raise RuntimeError(f"missing_runtime_paths:{','.join(missing_paths)}")

    catalog_items = load_ingredient_catalog()
    load_safety_rules()
    runtime_db = load_runtime_knowledge_db()

    knowledge_source = (
        "prebuilt_runtime_knowledge_db"
        if runtime_knowledge_path.exists()
        else "rebuilt_from_reference_knowledge_artifact"
    )
    return {
        "runtime_status": "ready",
        "ingredient_catalog_count": len(catalog_items),
        "interaction_rule_count": len(runtime_db.interaction_rules),
        "reference_count": len(runtime_db.references),
        "knowledge_source": knowledge_source,
        "repo_root": str(Path(root)),
    }
