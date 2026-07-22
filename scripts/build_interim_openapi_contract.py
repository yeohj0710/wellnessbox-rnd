from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402

DEFAULT_OUTPUT = ROOT / "data/contracts/wb_rnd_interim_openapi_surface_v1.json"


def _collect_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
            refs.add(reference.rsplit("/", 1)[-1])
        for item in value.values():
            refs.update(_collect_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_refs(item))
    return refs


def build_contract() -> dict[str, Any]:
    openapi = app.openapi()
    paths = {
        path: openapi["paths"][path]
        for path in sorted(openapi["paths"])
        if path.startswith("/v1/interim/")
    }
    all_schemas = openapi.get("components", {}).get("schemas", {})
    pending = _collect_refs(paths)
    schemas: dict[str, Any] = {}
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in schemas:
            continue
        schema = all_schemas[name]
        schemas[name] = schema
        pending.update(_collect_refs(schema) - schemas.keys())
    return {
        "schema_version": "wb_rnd_interim_openapi_surface_v1",
        "openapi_version": openapi["openapi"],
        "paths": paths,
        "component_schemas": {name: schemas[name] for name in sorted(schemas)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_contract(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale_interim_openapi_contract:{args.output}")
        print(f"interim OpenAPI contract is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote interim OpenAPI contract: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
