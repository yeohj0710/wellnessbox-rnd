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
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = "data/original_plan/contracts/engine_input_registry_v1.json"

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
        if isinstance(node, ast.JoinedStr):
            return {
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            }
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
        for statement in node.body:
            self.visit(statement)
        self._scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

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
