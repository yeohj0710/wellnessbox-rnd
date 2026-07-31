"""List the data files the measured engine reads, so a drafter can be checked.

`assert_source_is_independent` compares the declared source against a list of
forbidden names. That catches a drafter that announces itself as the engine. It
does not catch the case that actually happened: a drafter that declares an
innocent source string and then reads the engine's own rule file, so the engine
reproduces the answer by construction.

Deciding that by hand does not scale — the engine reads dozens of files and the
list moves. This script derives the list instead. It walks the engine packages,
matches every `data/**` artifact against their source, and writes what it found.

Roles matter for how a hit is read:

  vocabulary    a shared identifier space. An answer key has to use it or the
                comparison has nothing to join on. Reading it is not leakage.
  engine_logic  rules, policies and priors that decide the engine's output.
                An answer drawn from here is the engine's own answer.

Usage:
  python scripts/build_engine_input_registry.py
"""

from __future__ import annotations

import hashlib
import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src/wellnessbox_rnd"
DEFAULT_OUTPUT = "data/original_plan/contracts/engine_input_registry_v1.json"
SCHEMA = "engine_input_registry_v1"

# Packages that make up the system under test. `evals` drafts and measures,
# `governance` audits; neither decides an engine output, so neither counts.
ENGINE_PACKAGES: tuple[str, ...] = (
    "chat",
    "domain",
    "efficacy",
    "ingestion",
    "interim",
    "knowledge",
    "models",
    "optimizer",
    "orchestration",
    "policy",
    "safety",
    "simulation",
    "training",
)
EXCLUDED_PACKAGES: tuple[str, ...] = ("evals", "governance")

# Artifacts that exist to measure the engine, not to run it.
MEASUREMENT_PREFIXES: tuple[str, ...] = (
    "data/original_plan/kpi/",
    "data/frozen_eval/",
    "data/knowledge/external/",
)

VOCABULARY_PATHS: frozenset[str] = frozenset(
    {
        "data/catalog/ingredients.json",
        "data/contracts/wellnessbox_ingredient_identifier_map_v1.json",
    }
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def engine_sources() -> list[Path]:
    files: list[Path] = []
    for package in ENGINE_PACKAGES:
        directory = SOURCE_ROOT / package
        if directory.is_dir():
            files.extend(sorted(directory.rglob("*.py")))
    return files


def data_artifacts() -> list[Path]:
    return sorted(
        path
        for pattern in ("*.json", "*.jsonl")
        for path in (ROOT / "data").rglob(pattern)
        if path.is_file()
    )


def is_measurement_artifact(relative: str) -> bool:
    return any(relative.startswith(prefix) for prefix in MEASUREMENT_PREFIXES)


def readers_of(artifact: Path, sources: list[tuple[Path, str]]) -> list[str]:
    """Find engine modules that name this artifact.

    Both spellings are in use: a literal `"data/rules/safety_rules.json"` and a
    `repo_root() / "data" / "rules" / "safety_rules.json"` join. Matching the
    file name covers both without parsing the source.
    """
    needle = artifact.name
    return sorted(
        {
            module
            for path, text in sources
            if needle in text
            for module in [str(path.relative_to(SOURCE_ROOT)).replace("\\", "/")]
        }
    )


def build_registry() -> dict[str, Any]:
    sources = [(path, path.read_text(encoding="utf-8")) for path in engine_sources()]
    entries: list[dict[str, Any]] = []

    for artifact in data_artifacts():
        relative = str(artifact.relative_to(ROOT)).replace("\\", "/")
        if is_measurement_artifact(relative):
            continue
        readers = readers_of(artifact, sources)
        if not readers:
            continue
        entries.append(
            {
                "path": relative,
                "role": "vocabulary" if relative in VOCABULARY_PATHS else "engine_logic",
                "sha256": sha256_of(artifact),
                "read_by": readers,
            }
        )

    return {
        "schema_version": SCHEMA,
        "system_under_test": "wellnessbox_rnd_engine",
        "engine_packages": list(ENGINE_PACKAGES),
        "excluded_packages": list(EXCLUDED_PACKAGES),
        "measurement_prefixes": list(MEASUREMENT_PREFIXES),
        "note": (
            "정답 초안 생성기가 role=engine_logic 파일을 읽으면 그 정답은 엔진 자신의 값이다. "
            "role=vocabulary 는 대조에 필요한 공용 식별자라 읽어도 된다."
        ),
        "entry_count": len(entries),
        "engine_logic_count": sum(1 for item in entries if item["role"] == "engine_logic"),
        "entries": entries,
    }


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    registry = build_registry()
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(
        {
            "status": "READY",
            "output": str(target),
            "entry_count": registry["entry_count"],
            "engine_logic_count": registry["engine_logic_count"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
