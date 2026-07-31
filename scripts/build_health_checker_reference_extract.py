"""Extract an independent reference corpus for KPI answer keys.

KPI-1/3/4/5 score the engine against an answer a human produced. The answer must
come from a derivation the engine does not share, or the score measures the
engine against itself.

`건강상담 Checker` is such a source. It is a pharmacist counseling work the
project owner authored, published before this engine existed, and its evidence
layer does not overlap the engine's knowledge base: the engine cites NIH ODS,
NCCIH, CDC, ADA and PubMed, and the work appears nowhere in that base. The
extract below carries the page citation for every item so a reviewer can check
any case against the printed source.

This script reads the structured corpus and writes only what an answer-key
drafter needs. It records the source digest so the extract stays reproducible
without the original repository present.

Usage:
  python scripts/build_health_checker_reference_extract.py \\
      --source C:/dev/health-checker/src/data/assessment-runtime.json
"""

from __future__ import annotations

import hashlib
import json
import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = "C:/dev/health-checker/src/data/assessment-runtime.json"
DEFAULT_OUTPUT = "data/knowledge/external/health_checker_reference_extract_v1.json"
CATALOG_PATH = "data/catalog/ingredients.json"
SCHEMA = "health_checker_reference_extract_v1"

# Book nutrient name -> engine catalog key. `relationship` follows the pattern in
# `wellnessbox_ingredient_identifier_map_v1.json`: `book_broader` means the book
# names a wider group than the catalog key, so mapping loses specificity.
INGREDIENT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"^구연산 마그네슘$", "magnesium_glycinate", "book_narrower"),
    (r"^마그네슘$", "magnesium_glycinate", "book_broader"),
    (r"^L-테아닌$", "l_theanine", "equivalent"),
    (r"^비타민 C$", "vitamin_c", "equivalent"),
    (r"^아연$", "zinc", "equivalent"),
    (r"^비타민 B군", "vitamin_b_complex", "equivalent"),
    (r"^비타민 B(1|2|5|6|12)$", "vitamin_b_complex", "book_narrower"),
    (r"^엽산", "vitamin_b_complex", "book_narrower"),
    (r"^코엔자임Q10$", "coq10", "equivalent"),
    (r"^코큐텐", "coq10", "equivalent"),
    (r"^(유산균|프로바이오틱스)$", "probiotics", "equivalent"),
    (r"^(식이섬유|차전자피)$", "soluble_fiber", "book_broader"),
    (r"^비타민 D3?$", "vitamin_d3", "book_broader"),
    (r"^칼슘$", "calcium_citrate", "book_broader"),
    (r"^오메가-3$", "omega3", "equivalent"),
    (r"^베르베린$", "berberine", "equivalent"),
)

# Medication contexts must be traceable to the same source, so they are drawn
# from the work's own drug tables rather than invented here.
CONTEXT_DRUG_NAMES: tuple[str, ...] = (
    "Metformin",
    "Furosemide",
    "Levothyroxine",
    "Prednisolone",
    "Esomeprazole",
    "Aspirin",
    "Atorvastatin",
    "Amlodipine",
)


def digest(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plain(value: str) -> str:
    """Drop the source markup without touching the wording."""
    text = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def normalise_drug(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def catalog_keys(root: Path) -> set[str]:
    payload = json.loads((root / CATALOG_PATH).read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("ingredients", [])
    return {str(item["key"]) for item in items}


def map_ingredient(book_name: str) -> tuple[str, str] | None:
    for pattern, key, relationship in INGREDIENT_PATTERNS:
        if re.search(pattern, book_name):
            return key, relationship
    return None


def build_ingredient_map(nutrients: list[dict[str, Any]], keys: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for nutrient in nutrients:
        name = str(nutrient["canonicalName"])
        mapped = map_ingredient(name)
        if mapped is None or mapped[0] not in keys:
            continue
        rows.append(
            {
                "book_nutrient": name,
                "rnd_ingredient_key": mapped[0],
                "relationship": mapped[1],
            }
        )
    return sorted(rows, key=lambda row: (row["rnd_ingredient_key"], row["book_nutrient"]))


def nutrients_by_solution(nutrients: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group nutrient names by the solution row the work cites them in."""
    grouped: dict[str, list[str]] = {}
    for nutrient in nutrients:
        for evidence in nutrient.get("evidence", []):
            if not evidence.get("areaId"):
                continue
            grouped.setdefault(str(evidence["evidenceRaw"]), []).append(
                str(nutrient["canonicalName"])
            )
    return {key: sorted(set(value)) for key, value in grouped.items()}


def build_recommendation_cases(
    runtime: dict[str, Any], name_to_key: dict[str, str]
) -> list[dict[str, Any]]:
    grouped = nutrients_by_solution(runtime["nutrients"])
    cases: list[dict[str, Any]] = []

    for area in runtime["assessmentAreas"]:
        for solution in area.get("solutionGroups", []):
            key = f"{solution['targetRaw']} | {solution['recommendationsRaw']}"
            book_nutrients = grouped.get(key, [])
            if not book_nutrients:
                continue
            mapped = sorted({name_to_key[name] for name in book_nutrients if name in name_to_key})
            if not mapped:
                continue
            cases.append(
                {
                    "case_key": str(solution["id"]),
                    "area_id": str(area["id"]),
                    "area_title": plain(str(area["titleRaw"])),
                    "target": plain(str(solution["targetRaw"])),
                    "book_nutrients": book_nutrients,
                    "mapped_ingredients": mapped,
                    "out_of_catalog_nutrients": sorted(
                        name for name in book_nutrients if name not in name_to_key
                    ),
                    "source": {
                        "file": str(solution["source"]["file"]),
                        "page": int(solution["source"]["page"]),
                    },
                }
            )
    return sorted(cases, key=lambda case: case["case_key"])


def classify_interaction(cells: list[str], book_nutrient: str) -> str:
    """Tell a co-administration interaction from a plain depletion.

    The source table is `분류 | 약물 | 영양소 | 기전 | 상담`. Only the 영양소 cell
    carries the work's own `(상호작용형)` marker, so read that cell rather than the
    whole row — several depletion rows describe absorption in the 기전 cell and
    would otherwise be misread as interactions.
    """
    marker = "상호작용" in book_nutrient
    if len(cells) >= 3:
        marker = marker or "상호작용" in cells[2]
    return "absorption_interaction" if marker else "depletion"


def build_medication_contexts(
    runtime: dict[str, Any], name_to_key: dict[str, str]
) -> list[dict[str, Any]]:
    wanted = {normalise_drug(name) for name in CONTEXT_DRUG_NAMES}
    contexts: list[dict[str, Any]] = []

    for drug in runtime["drugs"]:
        aliases = {normalise_drug(drug["canonicalName"])}
        aliases.update(normalise_drug(alias) for alias in drug.get("aliasesRaw", []))
        if not (aliases & wanted):
            continue

        affected: dict[str, dict[str, Any]] = {}
        for depletion in drug.get("depletions", []):
            name = str(depletion["nutrientRaw"])
            key = name_to_key.get(re.sub(r"\s*\(.*\)$", "", name).strip())
            if key is None:
                continue
            cells = [cell.strip() for cell in plain(str(depletion["evidenceRaw"])).split("|")]
            affected[key] = {
                "rnd_ingredient_key": key,
                "book_nutrient": name,
                "kind": classify_interaction(cells, name),
                "counseling": cells[-1] if cells else "",
                "source": {
                    "file": str(depletion["source"]["file"]),
                    "page": int(depletion["source"]["page"]),
                },
            }

        if not affected:
            continue
        contexts.append(
            {
                "drug": str(drug["canonicalName"]),
                "aliases": sorted(str(alias) for alias in drug.get("aliasesRaw", [])),
                "affected_ingredients": [affected[key] for key in sorted(affected)],
            }
        )
    return sorted(contexts, key=lambda item: item["drug"])


def build_extract(runtime: dict[str, Any], *, root: Path, source_sha256: str) -> dict[str, Any]:
    keys = catalog_keys(root)
    ingredient_map = build_ingredient_map(runtime["nutrients"], keys)
    name_to_key = {row["book_nutrient"]: row["rnd_ingredient_key"] for row in ingredient_map}

    recommendation_cases = build_recommendation_cases(runtime, name_to_key)
    medication_contexts = build_medication_contexts(runtime, name_to_key)
    covered = {key for case in recommendation_cases for key in case["mapped_ingredients"]}

    payload = {
        "schema_version": SCHEMA,
        "source": {
            "work_title": "건강상담 Checker",
            "work_kind": "약사 상담용 출판 저작물",
            "artifact_path": "health-checker/src/data/assessment-runtime.json",
            "artifact_sha256": source_sha256,
            "rights_holder": "project_owner",
            "rights_note": "저작권자가 프로젝트 오너와 동일해 연구 내부 이용에 제약이 없다.",
        },
        "independence": {
            "system_under_test": "wellnessbox_rnd_recommendation_engine",
            "shared_evidence_with_engine": False,
            "engine_evidence_sources": [
                "NIH Office of Dietary Supplements",
                "NCCIH",
                "CDC",
                "ADA Standards of Care",
                "PubMed",
                "master_context",
            ],
            "check": (
                "엔진 지식베이스(reference_knowledge_base_v1) 19건은 모두 국제 기관·문헌이며 "
                "이 저작물을 인용하지 않는다. 따라서 정답 초안이 엔진 근거층을 되풀이하지 않는다."
            ),
        },
        "ingredient_map": ingredient_map,
        "recommendation_cases": recommendation_cases,
        "medication_contexts": medication_contexts,
        "coverage": {
            "book_nutrient_count": len(runtime["nutrients"]),
            "mapped_nutrient_count": len(ingredient_map),
            "catalog_key_count": len(keys),
            "catalog_keys_covered": sorted(covered),
            "catalog_keys_uncovered": sorted(keys - covered),
            "recommendation_case_count": len(recommendation_cases),
            "medication_context_count": len(medication_contexts),
        },
    }
    payload["content_sha256"] = digest(
        {
            "ingredient_map": ingredient_map,
            "recommendation_cases": recommendation_cases,
            "medication_contexts": medication_contexts,
        }
    )
    return payload


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="구조화 원문 코퍼스 경로")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="추출 결과 저장 경로")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_path = Path(args.source)
    if not source_path.is_file():
        print(json.dumps(
            {"status": "BLOCKED", "reason": "source_not_found", "path": str(source_path)},
            ensure_ascii=False, indent=2,
        ))
        return 2

    raw = source_path.read_bytes()
    runtime = json.loads(raw.decode("utf-8"))
    payload = build_extract(
        runtime, root=ROOT, source_sha256=hashlib.sha256(raw).hexdigest()
    )

    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(
        {"status": "READY", "output": str(target), **payload["coverage"]},
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
