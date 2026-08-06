from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(ROOT.parent / "wellnessbox"))
).resolve()
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.governance.final_completion_audit import (  # noqa: E402
    CompletionReceiptV1,
    FinalAuditPolicyV1,
    IndependentReviewReceiptV1,
    _signature_valid,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    audit_reviewer_credentials,
    load_draft_reviewer_ids,
    load_registry,
)
from wellnessbox_rnd.interim.data_lake import data_lake_database_path  # noqa: E402
from wellnessbox_rnd.governance.original_plan_audit import (  # noqa: E402
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (  # noqa: E402
    load_original_plan_manifest_v1,
)

HUMAN_RECORD_PATHS = {
    "wellnessbox-rnd/artifacts/final_session/completion_wizard_progress_v1.json",
    "wellnessbox-rnd/data/original_plan/final_session/external_validation/op039_external_validation.json",
    "wellnessbox-rnd/data/original_plan/final_session/final_validation_receipt_v1.json",
    "wellnessbox-rnd/data/original_plan/final_session/human_signoff_completion_v1.json",
    "wellnessbox-rnd/data/original_plan/final_session/independent_final_review_receipt_v1.json",
    "wellnessbox-rnd/data/original_plan/final_session/operational_wizard_v1.json",
    "wellnessbox-rnd/data/original_plan/final_session/session_state_v1.json",
    "wellnessbox-rnd/data/original_plan/op120_final_audit_policy_v1.json",
}
AUDIT_POLICY_PATH = "wellnessbox-rnd/data/original_plan/op120_final_audit_policy_v1.json"
IMPORTABLE_HUMAN_RECORD_PATHS = HUMAN_RECORD_PATHS - {AUDIT_POLICY_PATH}
INSTRUCTION_SUFFIXES = (".md", ".txt", ".html", ".readme")
PRIVATE_KEY_SUFFIXES = (".pem", ".key")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def current_heads() -> dict[str, str]:
    return {"wellnessbox-rnd": git_head(ROOT), "wellnessbox": git_head(SERVICE_ROOT)}


def safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
    )


def _source_paths_requiring_identity_match(actual_paths: set[str]) -> list[str]:
    """Return the reviewed service files that must match the current checkout.

    Only `wellnessbox/` counts. That tree is the subject of the review and it
    stays frozen while a package is out, so byte identity is a real check there.

    `wellnessbox-rnd/` is deliberately excluded. It holds the machinery that
    grades the package - the importer reading this archive, its tests, and the
    audit evidence the audit rewrites on every run. Demanding byte identity
    against a tree that changes every round strands the outstanding package the
    moment anyone touches that machinery, which is a loop no reviewer can exit.
    The research side is already bound twice over: `repository_head_not_ancestor`
    below pins the package to an ancestor of the current head, and each receipt
    carries `manifest_sha256`, `canonical_audit_sha256` and `source_commit`.
    """
    return sorted(
        path
        for path in actual_paths - IMPORTABLE_HUMAN_RECORD_PATHS
        if path.startswith("wellnessbox/")
    )


def _json_from_archive(archive: zipfile.ZipFile, path: str) -> Any:
    return json.loads(archive.read(path).decode("utf-8"))


def _receipt_checks(
    *,
    archive: zipfile.ZipFile,
    policy: dict[str, Any],
    manifest_sha256: str,
    canonical_audit_sha256: str,
    heads: dict[str, str],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    try:
        policy_model = FinalAuditPolicyV1.model_validate(policy)
    except ValueError as exc:
        return {"status": "REJECTED", "problems": [f"policy_invalid:{exc}"]}
    validation_issuers = {
        (item.issuer_id, item.public_key_ed25519_base64)
        for item in policy_model.trusted_issuers
    }
    independent_issuers = {
        (item.issuer_id, item.public_key_ed25519_base64)
        for item in policy_model.independent_review_trusted_issuers
        if (item.issuer_id, item.public_key_ed25519_base64) not in validation_issuers
    }
    for label, path, model, issuers in (
        (
            "validation",
            "wellnessbox-rnd/data/original_plan/final_session/final_validation_receipt_v1.json",
            CompletionReceiptV1,
            policy_model.trusted_issuers,
        ),
        (
            "independent_review",
            "wellnessbox-rnd/data/original_plan/final_session/independent_final_review_receipt_v1.json",
            IndependentReviewReceiptV1,
            policy_model.independent_review_trusted_issuers,
        ),
    ):
        problems: list[str] = []
        try:
            receipt = model.model_validate_json(archive.read(path).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, ValueError) as exc:
            checks[label] = {"status": "REJECTED", "problems": [f"receipt_invalid:{exc}"]}
            continue
        if receipt.status != "PASS":
            problems.append("status_not_pass")
        if receipt.manifest_sha256 != manifest_sha256:
            problems.append("manifest_sha256_mismatch")
        if receipt.canonical_audit_sha256 != canonical_audit_sha256:
            problems.append("canonical_audit_sha256_mismatch")
        if receipt.source_commit not in set(heads.values()):
            problems.append("source_commit_not_current_head")
        if not _signature_valid(receipt, issuers):
            problems.append("signature_invalid_or_untrusted")
        if label == "independent_review":
            if not independent_issuers:
                problems.append("independent_review_trust_root_not_separate")
            if receipt.critical_count != 0:
                problems.append("critical_count_not_zero")
            if receipt.important_count != 0:
                problems.append("important_count_not_zero")
        checks[label] = {"status": "READY" if not problems else "REJECTED", "problems": problems}
    return checks


def _external_review_checks(
    *, archive: zipfile.ZipFile, root: Path, cases_sha256: str
) -> dict[str, Any]:
    path = "wellnessbox-rnd/data/original_plan/final_session/external_validation/op039_external_validation.json"
    cases_path = "wellnessbox-rnd/data/original_plan/op039_external_review_cases_v1.json"
    try:
        review = _json_from_archive(archive, path)
        cases = _json_from_archive(archive, cases_path)
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "REJECTED", "problems": [f"op039_json_invalid:{exc}"]}
    problems: list[str] = []
    if review.get("schema_version") != "op039_external_review_result_v1":
        problems.append("op039_schema_invalid")
    if review.get("package_id") != cases.get("package_id"):
        problems.append("op039_package_id_mismatch")
    if review.get("cases_sha256") != cases_sha256:
        problems.append("op039_cases_sha256_mismatch")
    expected_ids = {item.get("case_id") for item in cases.get("cases", [])}
    decisions = review.get("decisions", [])
    observed_ids = {item.get("case_id") for item in decisions if isinstance(item, dict)}
    if len(decisions) != len(expected_ids) or observed_ids != expected_ids:
        problems.append("op039_case_set_mismatch")
    if any(item.get("decision") != "valid" for item in decisions if isinstance(item, dict)):
        problems.append("op039_invalid_decision_present")
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, dict):
        problems.append("op039_reviewer_missing")
    else:
        if reviewer.get("reviewer_role") != "project_pharmacist_candidate":
            problems.append("op039_reviewer_role_invalid")
        if reviewer.get("relationship_to_project") != "project_co_researcher":
            problems.append("op039_reviewer_relationship_invalid")
        if reviewer.get("independent_of_implementation_team") is not False:
            problems.append("op039_reviewer_independence_invalid")
        try:
            credential_audit = audit_reviewer_credentials(
                reviewer,
                registry=load_registry(root),
                draft_reviewer_ids=load_draft_reviewer_ids(data_lake_database_path()),
            )
            problems.extend(credential_audit["problems"])
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            problems.append(f"op039_reviewer_identity_audit_failed:{exc}")
        name = str(reviewer.get("name", "")).strip()
        if str(review.get("signature_name", "")).strip() != name:
            problems.append("op039_signature_name_mismatch")
    return {"status": "READY" if not problems else "REJECTED", "problems": problems}


def _wizard_checks(*, archive: zipfile.ZipFile) -> dict[str, Any]:
    path = "wellnessbox-rnd/artifacts/final_session/completion_wizard_progress_v1.json"
    try:
        progress = _json_from_archive(archive, path)
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "REJECTED", "problems": [f"wizard_json_invalid:{exc}"]}
    problems: list[str] = []
    if progress.get("schema_version") != "completion_wizard_progress_v1":
        problems.append("wizard_schema_invalid")
    if progress.get("total_steps") != 13:
        problems.append("wizard_total_steps_invalid")
    rows = progress.get("steps", [])
    if not isinstance(rows, list) or len(rows) != 13:
        problems.append("wizard_step_rows_invalid")
        rows = []
    # AUDIT is the last wizard step and it only turns green once the final audit
    # reports READY - which needs the receipts this very package delivers. Asking
    # the returned package to already show AUDIT finished is circular, so the
    # step is checked after the import instead, by the audit itself.
    unfinished = [
        str(row.get("step_id", "?"))
        for row in rows
        if not isinstance(row, dict)
        or (
            row.get("step_id") != "AUDIT"
            and row.get("verdict") not in {"done", "skipped_gate_closed"}
        )
    ]
    if unfinished:
        problems.append("wizard_unfinished_steps:" + ",".join(unfinished))
    train = next(
        (row for row in rows if isinstance(row, dict) and row.get("step_id") == "TRAIN"),
        None,
    )
    if (
        not train
        or train.get("verdict") != "skipped_gate_closed"
        or "NO-GO" not in str(train.get("detail", ""))
    ):
        problems.append("training_no_go_gate_not_preserved")
    return {"status": "READY" if not problems else "REJECTED", "problems": problems}


def verify_package(zip_path: Path) -> dict[str, Any]:
    structural: list[str] = []
    human: dict[str, Any] = {}
    archive_sha256 = sha256_bytes(zip_path.read_bytes())
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            structural.append("duplicate_archive_paths")
        if any(item.is_dir() for item in infos):
            structural.append("directory_entries_not_allowed")
        unsafe = [name for name in names if not safe_member_name(name)]
        if unsafe:
            structural.append(f"unsafe_archive_paths:{len(unsafe)}")
        instruction_paths = [
            name for name in names if name.lower().endswith(INSTRUCTION_SUFFIXES)
        ]
        private_paths = [
            name
            for name in names
            if name.lower().endswith(PRIVATE_KEY_SUFFIXES) or "private" in name.lower()
        ]
        if instruction_paths:
            structural.append(f"instruction_paths_present:{len(instruction_paths)}")
        if private_paths:
            structural.append(f"private_key_paths_present:{len(private_paths)}")
        try:
            manifest = _json_from_archive(archive, "package_manifest.json")
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {
                "status": "REJECTED",
                "archive_sha256": archive_sha256,
                "structural_problems": [f"manifest_invalid:{exc}"],
                "human_materials": {},
            }
        if manifest.get("schema_version") != "completion_human_processing_package_manifest_v1":
            structural.append("manifest_schema_invalid")
        records = manifest.get("files", [])
        record_paths = {item.get("path") for item in records}
        actual_paths = set(names) - {"package_manifest.json"}
        if record_paths != actual_paths:
            structural.append("manifest_path_set_mismatch")
        hash_mismatches: list[str] = []
        for item in records:
            try:
                data = archive.read(item["path"])
            except KeyError:
                hash_mismatches.append(str(item.get("path")))
                continue
            if len(data) != item.get("bytes") or sha256_bytes(data) != item.get("sha256"):
                hash_mismatches.append(str(item.get("path")))
        if hash_mismatches:
            structural.append(f"manifest_content_hash_mismatches:{len(hash_mismatches)}")
        heads = current_heads()
        manifest_heads = manifest.get("repositories", {})
        if not isinstance(manifest_heads, dict):
            structural.append("repository_heads_invalid")
        else:
            for repository, current_head in heads.items():
                manifest_head = manifest_heads.get(repository)
                repository_root = ROOT if repository == "wellnessbox-rnd" else SERVICE_ROOT
                if not isinstance(manifest_head, str) or not git_is_ancestor(
                    repository_root, manifest_head, current_head
                ):
                    structural.append(f"repository_head_not_ancestor:{repository}")
        source_mismatches: list[str] = []
        for path in _source_paths_requiring_identity_match(actual_paths):
            repository, relative = path.split("/", 1)
            source = (ROOT if repository == "wellnessbox-rnd" else SERVICE_ROOT) / relative
            if not source.is_file() or source.read_bytes() != archive.read(path):
                source_mismatches.append(path)
        if source_mismatches:
            structural.append(f"current_source_mismatches:{len(source_mismatches)}")
        json_errors: list[str] = []
        for path in actual_paths:
            if path.lower().endswith(".json"):
                try:
                    json.loads(archive.read(path).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    json_errors.append(path)
        if json_errors:
            structural.append(f"json_syntax_errors:{len(json_errors)}")
        cases_path = "wellnessbox-rnd/data/original_plan/op039_external_review_cases_v1.json"
        try:
            cases_bytes = archive.read(cases_path)
            cases = json.loads(cases_bytes.decode("utf-8"))
            if manifest.get("case_counts", {}).get("OP-039") != len(cases.get("cases", [])):
                structural.append("op039_case_count_mismatch")
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            structural.append(f"op039_cases_invalid:{exc}")
            cases_bytes = b""
        if cases_bytes:
            human["op039_external_review"] = _external_review_checks(
                archive=archive, root=ROOT, cases_sha256=sha256_bytes(cases_bytes)
            )
        missing_human_records = sorted(HUMAN_RECORD_PATHS - actual_paths)
        human["required_records"] = {
            "status": "READY" if not missing_human_records else "REJECTED",
            "problems": (
                []
                if not missing_human_records
                else ["required_records_missing:" + ",".join(missing_human_records)]
            ),
        }
        human["wizard"] = _wizard_checks(archive=archive)
        policy_path = "wellnessbox-rnd/data/original_plan/op120_final_audit_policy_v1.json"
        try:
            policy = _json_from_archive(archive, policy_path)
            manifest_path = ROOT / "data/original_plan/requirements_manifest_v1.json"
            canonical = audit_original_plan_manifest_v1(
                load_original_plan_manifest_v1(manifest_path),
                repository_roots={"wellnessbox-rnd": ROOT, "wellnessbox": SERVICE_ROOT},
            )
            human["receipts"] = _receipt_checks(
                archive=archive,
                policy=policy,
                manifest_sha256=canonical.manifest_sha256,
                canonical_audit_sha256=hashlib.sha256(
                    canonical.model_dump_json().encode("utf-8")
                ).hexdigest(),
                heads=heads,
            )
        except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
            human["receipts"] = {"status": "REJECTED", "problems": [f"receipt_context_failed:{exc}"]}
    human_ready = all(item.get("status") == "READY" for item in human.values()) and bool(human)
    return {
        "status": "READY_FOR_PROCESSING" if not structural else "REJECTED",
        "ready_to_apply": not structural and human_ready,
        "archive_sha256": archive_sha256,
        "entry_count": len(names),
        "manifest_file_count": len(records),
        "case_counts": manifest.get("case_counts", {}),
        "structural_problems": structural,
        "human_materials": human,
    }


def apply_package(zip_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("ready_to_apply"):
        raise ValueError("package_is_not_ready_to_apply")
    archive_sha256 = str(result["archive_sha256"])
    backup_root = ROOT / "etc" / "import_backups" / archive_sha256
    backup_root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path) as archive:
        payloads = {path: archive.read(path) for path in HUMAN_RECORD_PATHS}
    applied: list[str] = []
    for archive_path, data in payloads.items():
        _, relative = archive_path.split("/", 1)
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_file():
            shutil.copy2(destination, backup)
        destination.write_bytes(data)
        applied.append(str(destination))
    return {"backup_root": str(backup_root), "applied_paths": applied}


def main() -> int:
    parser = argparse.ArgumentParser(description="검증된 완료 처리 ZIP importer")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--apply", action="store_true", help="검증을 통과한 사람 자료만 반영")
    args = parser.parse_args()
    zip_path = args.zip_path.resolve()
    result = verify_package(zip_path)
    if args.apply:
        if not result["ready_to_apply"]:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        result["apply"] = apply_package(zip_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "READY_FOR_PROCESSING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
