"""The integrity audit has to separate documenting a fault from committing one.

A module that warns about `safety_rules.json` in its docstring is not reading it.
A module that assigns the path to a constant is. Raw-text matching calls both a
read, which would flag the audit's own explanation as the thing it forbids.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_answer_key_integrity import drafter_source_index
from wellnessbox_rnd.evals.answer_key_integrity import (
    audit_drafter_source,
    audit_review_effort,
    load_registry,
    read_path_string_literals,
)

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "src/wellnessbox_rnd/evals"
REGISTRY = ROOT / "data/original_plan/contracts/engine_input_registry_v1.json"

pytestmark = pytest.mark.skipif(
    not REGISTRY.is_file(),
    reason="engine input registry not built; run scripts/build_engine_input_registry.py",
)


def test_registry_marks_the_engine_rule_file_as_engine_logic() -> None:
    registry = load_registry(ROOT)
    roles = {entry["path"]: entry["role"] for entry in registry["entries"]}
    assert roles["data/rules/safety_rules.json"] == "engine_logic"
    assert roles["data/catalog/ingredients.json"] == "vocabulary"


def test_docstring_mentions_are_not_counted_as_reads(tmp_path: Path) -> None:
    module = tmp_path / "documents_only.py"
    module.write_text(
        '"""This module explains that data/rules/safety_rules.json is off limits."""\n'
        "VALUE = 1\n",
        encoding="utf-8",
    )
    assert not any("safety_rules" in item for item in read_path_string_literals(module))
    assert audit_drafter_source([module], load_registry(ROOT))["verdict"] == "PASS"


def test_declaration_only_constants_are_not_counted_as_reads(tmp_path: Path) -> None:
    module = tmp_path / "declares_engine_path.py"
    module.write_text(
        'BLINDED_FROM = ("data/rules/safety_rules.json",)\n',
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_builtin_open_is_counted_as_a_read(tmp_path: Path) -> None:
    module = tmp_path / "reads_engine.py"
    module.write_text(
        'RULES = "data/rules/safety_rules.json"\n'
        "with open(RULES, encoding='utf-8') as handle:\n"
        "    DATA = handle.read()\n",
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "FAIL"
    assert "data/rules/safety_rules.json" in result["reads_engine_logic"]


def test_path_join_spelling_is_counted_as_a_read(tmp_path: Path) -> None:
    """`repo_root() / "data" / "rules" / "safety_rules.json"` must not slip past."""
    module = tmp_path / "joins_path.py"
    module.write_text(
        'from pathlib import Path\n'
        'PATH = Path("x") / "data" / "rules" / "safety_rules.json"\n'
        'DATA = PATH.read_text(encoding="utf-8")\n',
        encoding="utf-8",
    )
    assert audit_drafter_source([module], load_registry(ROOT))["verdict"] == "FAIL"


def test_reference_corpus_drafter_is_independent() -> None:
    module = EVALS / "reference_corpus_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_blinded_drafter_declarations_are_not_reads() -> None:
    module = EVALS / "blinded_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_drafter_source_index_is_indicator_specific() -> None:
    index = drafter_source_index()
    kpi4 = {path.name for path in index[("KPI-4", "health_checker_reference_extract_v1")]}
    kpi5 = {path.name for path in index[("KPI-5", "health_checker_reference_extract_v1")]}
    assert kpi4 == {"blinded_drafters.py"}
    assert kpi5 == {"reference_corpus_drafters.py"}


def test_priors_drafter_is_not_independent() -> None:
    """Recorded so the finding stays visible if the module is edited later."""
    module = EVALS / "answer_key_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "FAIL"
    assert "data/rules/safety_rules.json" in result["reads_engine_logic"]


def test_impossibly_fast_review_fails() -> None:
    workbench = {
        "decisions": {
            f"case-{index:03}": {
                "action": "accepted",
                "decided_at": f"2026-07-31T08:20:{21 + index * 0.04:06.3f}Z".replace(
                    "T08:20:2", "T08:20:2"
                ),
            }
            for index in range(10)
        }
    }
    # Rebuild with real spacing: ten decisions inside half a second.
    for index, key in enumerate(workbench["decisions"]):
        workbench["decisions"][key]["decided_at"] = (
            f"2026-07-31T08:20:{21 + index * 0.04:06.3f}Z"
        )
    result = audit_review_effort(workbench)
    assert result["verdict"] == "FAIL"
    assert result["seconds_per_decision"] < 1.0


def test_paced_review_passes() -> None:
    workbench = {
        "decisions": {
            f"case-{index:03}": {
                "action": "accepted",
                "decided_at": f"2026-07-31T08:{20 + index}:00Z",
            }
            for index in range(5)
        }
    }
    assert audit_review_effort(workbench)["verdict"] == "PASS"


def test_review_with_too_few_decisions_is_not_failed() -> None:
    assert audit_review_effort({"decisions": {}})["verdict"] == "PASS"


def test_current_kpi1_and_kpi5_reviews_are_flagged() -> None:
    """The seals on disk came from 100 accepts in under four seconds."""
    for indicator in ("kpi1", "kpi5"):
        path = ROOT / f"data/original_plan/kpi/workbench/{indicator}_workbench_v1.json"
        if not path.is_file():
            continue
        workbench = json.loads(path.read_text(encoding="utf-8"))
        if not workbench.get("decisions"):
            continue
        assert audit_review_effort(workbench)["verdict"] == "FAIL"
