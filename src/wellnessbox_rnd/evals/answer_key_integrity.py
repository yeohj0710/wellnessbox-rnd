"""Check the two things that make an answer key worth scoring against.

`assert_source_is_independent` compares a declared string against a deny list, and
`summarise_adjudication` reports the edit rate. Both are useful and both were in
place, yet two failures still got through:

  source     a drafter declared an innocent source name and then read the
             engine's own rule file, so the engine reproduces the answer by
             construction. The string check cannot see that.
  review     100 cases were accepted in four seconds. The edit rate warning
             fired, but a warning does not stop a seal, and the seal now carries
             a named reviewer for a review that did not happen.

Neither is a judgement call. A drafter either reads an engine input or it does
not, and a decision either had time to be read or it did not. This module answers
both mechanically so the answer is the same whoever asks.
"""

from __future__ import annotations

import ast
import importlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = "data/original_plan/contracts/engine_input_registry_v1.json"
WORKBENCH_DIR = "data/original_plan/kpi/workbench"
SEAL_DIR = "data/original_plan/kpi/seals"
DRAFTER_PACKAGE = "wellnessbox_rnd.evals"
DRAFTER_MODULES = (
    "answer_key_drafters",
    "reference_corpus_drafters",
    "blinded_drafters",
)
INDICATORS = ("KPI-1", "KPI-3", "KPI-4", "KPI-5")

# A case needs to be read before it is decided. One second per case is far below
# anything a person can do and still have looked; it is a floor, not a target.
MIN_SECONDS_PER_DECISION = 1.0


def load_registry(root: Path) -> dict[str, Any]:
    path = Path(root) / REGISTRY_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"engine_input_registry_missing:{path}. "
            "먼저 scripts/build_engine_input_registry.py 를 실행하세요."
        )
    return json.loads(path.read_text(encoding="utf-8"))


class _ReadPathVisitor(ast.NodeVisitor):
    """Collect path literals that flow into an actual file-read operation."""

    _READ_METHODS = frozenset({"open", "read_bytes", "read_text"})

    def __init__(self) -> None:
        self._scopes: list[dict[str, ast.AST]] = [{}]
        self.literals: set[str] = set()

    def _bind(self, target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._scopes[-1][target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._bind(item, value)

    def _resolve_name(self, name: str) -> ast.AST | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _path_literals(self, node: ast.AST, seen: set[str] | None = None) -> set[str]:
        seen = set() if seen is None else seen
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            if node.id in seen:
                return set()
            value = self._resolve_name(node.id)
            return (
                set()
                if value is None
                else self._path_literals(value, seen | {node.id})
            )
        if isinstance(node, ast.BinOp):
            return self._path_literals(node.left, seen) | self._path_literals(
                node.right, seen
            )
        if isinstance(node, ast.Attribute):
            return self._path_literals(node.value, seen)
        if isinstance(node, ast.Subscript):
            return self._path_literals(node.value, seen)
        if isinstance(node, ast.Call):
            literals = self._path_literals(node.func, seen)
            for argument in node.args:
                literals |= self._path_literals(argument, seen)
            return literals
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            literals: set[str] = set()
            for item in node.elts:
                literals |= self._path_literals(item, seen)
            return literals
        if isinstance(node, ast.Dict):
            literals: set[str] = set()
            for item in (*node.keys, *node.values):
                if item is not None:
                    literals |= self._path_literals(item, seen)
            return literals
        if isinstance(node, ast.JoinedStr):
            literals: set[str] = set()
            for part in node.values:
                literals |= self._path_literals(part, seen)
            return literals
        if isinstance(node, ast.FormattedValue):
            return self._path_literals(node.value, seen)
        return set()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._bind(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            self._bind(node.target, node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scopes.append({})
        arguments = (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
        for argument in arguments:
            self._scopes[-1][argument.arg] = ast.Constant(value=None)
        if node.args.vararg is not None:
            self._scopes[-1][node.args.vararg.arg] = ast.Constant(value=None)
        if node.args.kwarg is not None:
            self._scopes[-1][node.args.kwarg.arg] = ast.Constant(value=None)
        for statement in node.body:
            self.visit(statement)
        self._scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind(node.target, node.iter)
        for statement in (*node.body, *node.orelse):
            self.visit(statement)

    visit_AsyncFor = visit_For

    def _visit_comprehension(
        self,
        generators: list[ast.comprehension],
        values: tuple[ast.AST, ...],
    ) -> None:
        self._scopes.append({})
        for generator in generators:
            self.visit(generator.iter)
            self._bind(generator.target, generator.iter)
            for condition in generator.ifs:
                self.visit(condition)
        for value in values:
            self.visit(value)
        self._scopes.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, (node.key, node.value))

    def visit_Call(self, node: ast.Call) -> None:
        path_nodes: list[ast.AST] = []
        if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
            path_nodes.append(node.args[0])
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in self._READ_METHODS
        ):
            path_nodes.append(node.func.value)

        for path_node in path_nodes:
            self.literals |= self._path_literals(path_node)
        self.generic_visit(node)


def read_path_string_literals(module_path: Path) -> set[str]:
    """Return literals used to build paths passed to file-read operations.

    Docstrings and declaration-only constants such as `BLINDED_FROM` are not
    reads. A literal counts only when AST data flow reaches `open()`,
    `Path.open()`, `Path.read_text()` or `Path.read_bytes()`.
    """
    tree = ast.parse(Path(module_path).read_text(encoding="utf-8"))
    visitor = _ReadPathVisitor()
    visitor.visit(tree)
    return visitor.literals


def audit_drafter_source(
    module_paths: list[Path], registry: dict[str, Any]
) -> dict[str, Any]:
    """Report which engine inputs the modules behind a draft source read.

    Matching is on the artifact file name after AST data-flow analysis finds a
    real file-read call. This catches both a literal path and a
    `repo_root() / "data" / ...` join without treating a deny-list declaration
    as a read.
    """
    literals: set[str] = set()
    for path in module_paths:
        literals |= read_path_string_literals(path)

    engine_logic: list[str] = []
    vocabulary: list[str] = []
    for entry in registry["entries"]:
        name = Path(entry["path"]).name
        if not any(name in literal for literal in literals):
            continue
        (engine_logic if entry["role"] == "engine_logic" else vocabulary).append(entry["path"])

    return {
        "modules": sorted(str(path).replace("\\", "/") for path in module_paths),
        "reads_engine_logic": sorted(engine_logic),
        "reads_vocabulary": sorted(vocabulary),
        "independent": not engine_logic,
        "verdict": "PASS" if not engine_logic else "FAIL",
        "reason": (
            ""
            if not engine_logic
            else "정답이 엔진 자신의 규칙·정책 파일에서 나온다. 엔진은 정의상 이 답을 맞힌다."
        ),
    }


def _parse(stamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def audit_review_effort(workbench: dict[str, Any]) -> dict[str, Any]:
    """Report whether the recorded decisions had time to be decisions."""
    decisions = list(workbench.get("decisions", {}).values())
    settled = [item for item in decisions if item.get("action") in {"accepted", "edited"}]
    stamps = sorted(filter(None, (_parse(item.get("decided_at", "")) for item in settled)))

    if len(stamps) < 2:
        return {
            "decision_count": len(settled),
            "elapsed_seconds": None,
            "seconds_per_decision": None,
            "edit_rate_pct": 0.0,
            "verdict": "PASS" if not settled else "REVIEW",
            "reason": "판단 기록이 시간 비교를 하기에 부족하다." if settled else "",
        }

    elapsed = (stamps[-1] - stamps[0]).total_seconds()
    per_decision = elapsed / (len(stamps) - 1)
    edited = sum(1 for item in settled if item.get("action") == "edited")
    edit_rate = round(100.0 * edited / len(settled), 2)
    too_fast = per_decision < MIN_SECONDS_PER_DECISION

    return {
        "decision_count": len(settled),
        "elapsed_seconds": round(elapsed, 3),
        "seconds_per_decision": round(per_decision, 3),
        "edit_rate_pct": edit_rate,
        "verdict": "FAIL" if too_fast else "PASS",
        "reason": (
            f"{len(settled)}건을 {elapsed:.1f}초에 판단했다. 건당 {per_decision:.2f}초로는 "
            "사례를 읽을 수 없다. 자동 수락으로 보아야 한다."
            if too_fast
            else ""
        ),
    }


def audit_indicator(
    *,
    indicator_id: str,
    workbench: dict[str, Any],
    drafter_modules: list[Path],
    registry: dict[str, Any],
    seal_exists: bool,
) -> dict[str, Any]:
    sources = sorted({draft.get("draft_source", "") for draft in workbench.get("drafts", [])})
    source_audit = (
        audit_drafter_source(drafter_modules, registry)
        if drafter_modules
        else {
            "modules": [],
            "verdict": "REVIEW",
            "reason": "이 draft_source 를 만든 모듈을 찾지 못했다. 사람이 확인해야 한다.",
            "reads_engine_logic": [],
            "reads_vocabulary": [],
            "independent": None,
        }
    )
    review_audit = audit_review_effort(workbench)
    verdicts = {source_audit["verdict"], review_audit["verdict"]}
    verdict = "FAIL" if "FAIL" in verdicts else ("REVIEW" if "REVIEW" in verdicts else "PASS")

    return {
        "indicator_id": indicator_id,
        "draft_sources": sources,
        "case_count": len(workbench.get("drafts", [])),
        "source_independence": source_audit,
        "review_effort": review_audit,
        "seal_exists": seal_exists,
        "verdict": verdict,
        "seal_must_be_discarded": verdict == "FAIL" and seal_exists,
    }


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def drafter_source_index(root: Path) -> dict[tuple[str, str], set[Path]]:
    """Map an indicator and declared source to the module that produced it."""
    index: dict[tuple[str, str], set[Path]] = {}
    for name in DRAFTER_MODULES:
        try:
            module = importlib.import_module(f"{DRAFTER_PACKAGE}.{name}")
        except ImportError:
            continue
        path = (
            Path(root)
            / "src"
            / DRAFTER_PACKAGE.replace(".", "/")
            / f"{name}.py"
        )
        sources = getattr(module, "DRAFT_SOURCES", None)
        if isinstance(sources, dict):
            for indicator_id, source in sources.items():
                if isinstance(indicator_id, str) and isinstance(source, str):
                    index.setdefault((indicator_id, source), set()).add(path)
                    index.setdefault(
                        (indicator_id, f"{source}@{name}"),
                        set(),
                    ).add(path)
            continue

        source = getattr(module, "DRAFT_SOURCE", None)
        drafters = getattr(module, "DRAFTERS", {})
        if isinstance(source, str) and isinstance(drafters, dict):
            for indicator_id in drafters:
                if isinstance(indicator_id, str):
                    index.setdefault((indicator_id, source), set()).add(path)
                    index.setdefault(
                        (indicator_id, f"{source}@{name}"),
                        set(),
                    ).add(path)
    return index


def audit_repository(
    root: Path,
    *,
    indicators: tuple[str, ...] = INDICATORS,
) -> dict[str, Any]:
    """Run the canonical integrity audit against repository workbenches."""
    root = Path(root)
    registry = load_registry(root)
    index = drafter_source_index(root)
    results: list[dict[str, Any]] = []

    for indicator_id in indicators:
        workbench_path = root / WORKBENCH_DIR / (
            f"{_slug(indicator_id)}_workbench_v1.json"
        )
        if not workbench_path.is_file():
            continue
        workbench = json.loads(workbench_path.read_text(encoding="utf-8"))
        sources = {
            draft.get("draft_source", "")
            for draft in workbench.get("drafts", [])
        }
        modules = sorted(
            {
                path
                for source in sources
                for path in index.get((indicator_id, source), set())
            }
        )
        seal_path = (
            root
            / SEAL_DIR
            / f"{_slug(indicator_id)}_reference_seal_v1.json"
        )
        seal = (
            json.loads(seal_path.read_text(encoding="utf-8"))
            if seal_path.is_file()
            else None
        )
        indicator_audit = audit_indicator(
            indicator_id=indicator_id,
            workbench=workbench,
            drafter_modules=modules,
            registry=registry,
            seal_exists=seal is not None,
        )
        draft_ids = {
            item.get("case_id")
            for item in workbench.get("drafts", [])
            if item.get("case_id")
        }
        decided_ids = {
            case_id
            for case_id, decision in workbench.get("decisions", {}).items()
            if decision.get("action") in {"accepted", "edited", "rejected"}
        }
        seal_audit_verdict = (
            seal.get("provenance", {})
            .get("integrity_audit", {})
            .get("verdict")
            if seal is not None
            else None
        )
        indicator_audit["workbench_complete"] = draft_ids == decided_ids
        indicator_audit["seal_integrity_audit_verdict"] = seal_audit_verdict
        indicator_audit["completion_ready"] = bool(
            indicator_audit["verdict"] == "PASS"
            and indicator_audit["workbench_complete"]
            and seal is not None
            and seal.get("meets_minimum_sample")
            and seal_audit_verdict == "PASS"
        )
        results.append(indicator_audit)

    failed = [item for item in results if item["verdict"] == "FAIL"]
    needs_review = [item for item in results if item["verdict"] == "REVIEW"]
    complete = len(results) == len(indicators)
    completion_blockers = [
        item["indicator_id"]
        for item in results
        if not item["completion_ready"]
    ]
    if not complete:
        present = {item["indicator_id"] for item in results}
        completion_blockers.extend(
            indicator_id for indicator_id in indicators if indicator_id not in present
        )
    return {
        "schema_version": "answer_key_integrity_audit_v1",
        "indicator_count": len(results),
        "passed": sum(1 for item in results if item["verdict"] == "PASS"),
        "failed": len(failed),
        "needs_review": len(needs_review),
        "seals_to_discard": [
            item["indicator_id"]
            for item in results
            if item["seal_must_be_discarded"]
        ],
        "status": (
            "READY"
            if complete and not failed and not needs_review
            else "BLOCKED"
        ),
        "completion_status": (
            "READY" if complete and not completion_blockers else "BLOCKED"
        ),
        "completion_blockers": sorted(set(completion_blockers)),
        "indicators": results,
    }


def sealing_readiness(
    *,
    indicator_audit: dict[str, Any],
    workbench: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless the audit passes and every draft has a decision."""
    if indicator_audit.get("verdict") != "PASS":
        return {
            "status": "BLOCKED",
            "reason": "answer_key_integrity_audit_failed",
            "indicator_id": indicator_audit.get("indicator_id"),
            "integrity_audit": indicator_audit,
        }

    draft_ids = {
        item.get("case_id")
        for item in workbench.get("drafts", [])
        if item.get("case_id")
    }
    decisions = workbench.get("decisions", {})
    decided_ids = {
        case_id
        for case_id, decision in decisions.items()
        if decision.get("action") in {"accepted", "edited", "rejected"}
    }
    pending = sorted(draft_ids - decided_ids)
    if pending:
        return {
            "status": "BLOCKED",
            "reason": "adjudication_incomplete",
            "indicator_id": indicator_audit.get("indicator_id"),
            "pending": len(pending),
            "integrity_audit": indicator_audit,
        }
    return {
        "status": "READY",
        "indicator_id": indicator_audit.get("indicator_id"),
        "integrity_audit": indicator_audit,
    }


def audit_sealing_readiness(root: Path, indicator_id: str) -> dict[str, Any]:
    """Load the canonical workbench and return its pre-seal gate result."""
    root = Path(root)
    try:
        report = audit_repository(root, indicators=(indicator_id,))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {
            "status": "BLOCKED",
            "reason": "answer_key_integrity_audit_failed",
            "indicator_id": indicator_id,
            "integrity_audit": {
                "indicator_id": indicator_id,
                "verdict": "REVIEW",
                "reason": str(exc),
            },
        }
    audits = {
        item["indicator_id"]: item
        for item in report["indicators"]
    }
    indicator_audit = audits.get(indicator_id)
    if indicator_audit is None:
        return {
            "status": "BLOCKED",
            "reason": "answer_key_integrity_audit_failed",
            "indicator_id": indicator_id,
            "integrity_audit": {
                "indicator_id": indicator_id,
                "verdict": "REVIEW",
                "reason": "canonical_workbench_not_found",
            },
        }
    workbench_path = root / WORKBENCH_DIR / (
        f"{_slug(indicator_id)}_workbench_v1.json"
    )
    workbench = json.loads(workbench_path.read_text(encoding="utf-8"))
    return sealing_readiness(
        indicator_audit=indicator_audit,
        workbench=workbench,
    )
