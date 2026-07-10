from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from wellnessbox_rnd.interim.bootstrap import bootstrap_operational_evidence
from wellnessbox_rnd.interim.importer import (
    import_interim_package,
    register_retrained_package,
)
from wellnessbox_rnd.interim.kpi import evaluate_proxy_kpis
from wellnessbox_rnd.interim.manifest import validate_interim_package
from wellnessbox_rnd.interim.reports import generate_release, verify_release
from wellnessbox_rnd.interim.store import InterimStore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = Path(
    os.getenv(
        "WB_RND_INTERIM_PACKAGE_DIR",
        "C:/dev/wellnessbox_tips_interim_simulation_package",
    )
)
DEFAULT_DATABASE = Path(
    os.getenv(
        "WB_RND_INTERIM_DATABASE",
        str(REPO_ROOT / "artifacts" / "tips" / "interim" / "interim.sqlite3"),
    )
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WellnessBox interim proxy pipeline")
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE_ROOT)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("verify-package")
    migrate = subparsers.add_parser("migrate")
    migrate.add_argument("--clean", action="store_true")
    importer = subparsers.add_parser("import")
    importer.add_argument("--max-records-per-split", type=int)
    subparsers.add_parser("evaluate")
    subparsers.add_parser("status")
    subparsers.add_parser("bootstrap")
    subparsers.add_parser("report")
    subparsers.add_parser("verify-release")

    retrain = subparsers.add_parser("retrain")
    retrain.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "artifacts" / "tips" / "interim" / "retrained",
    )
    retrain.add_argument("--small", action="store_true")

    all_command = subparsers.add_parser("all")
    all_command.add_argument("--retrain", action="store_true")
    all_command.add_argument("--verify", action="store_true")
    return parser


def _json_default(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    return value


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=_json_default))


def _remove_database(database: Path) -> None:
    if database.exists():
        database.unlink()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{database}{suffix}")
        if sidecar.exists():
            sidecar.unlink()


def _retrain(package_root: Path, output_dir: Path, *, small: bool) -> None:
    script = package_root / "scripts" / "run_interim_proxy_research.py"
    sizes = (
        (2_000, 400, 300, 300, 120, 20)
        if small
        else (
            120_000,
            15_000,
            10_000,
            5_000,
            240,
            60,
        )
    )
    train, validation, calibration, test, effect_n, linkage_per_source = sizes
    command = [
        sys.executable,
        str(script),
        "--output-dir",
        str(output_dir),
        "--train",
        str(train),
        "--validation",
        str(validation),
        "--calibration",
        str(calibration),
        "--test",
        str(test),
        "--effect-n",
        str(effect_n),
        "--linkage-per-source",
        str(linkage_per_source),
    ]
    subprocess.run(command, cwd=package_root, check=True)


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _register_retrain(store: InterimStore, output_dir: Path) -> str:
    rollback = store.scalar(
        "select model_id from model_versions order by created_at desc, model_id desc limit 1"
    )
    return register_retrained_package(
        store,
        output_dir,
        code_commit=_git_commit(),
        rollback_model_id=str(rollback) if rollback else None,
    )


def _report(store: InterimStore, package_root: Path) -> object:
    return generate_release(
        store,
        repo_root=REPO_ROOT,
        source_package=package_root,
        retrained_package=REPO_ROOT / "artifacts" / "tips" / "interim" / "retrained",
    )


def _status(store: InterimStore) -> dict[str, object]:
    if not store.is_migrated():
        return {"migrated": False, "database": str(store.database_path)}
    counts = {
        table: int(store.scalar(f"select count(*) from {table}"))
        for table in (
            "proxy_cases",
            "pro_observations",
            "adverse_events",
            "connector_sessions",
            "evaluation_cases",
            "model_versions",
            "kpi_results",
        )
    }
    return {"migrated": True, "database": str(store.database_path), "counts": counts}


def main() -> int:
    args = build_parser().parse_args()
    store = InterimStore(args.database)

    if args.command == "verify-package":
        result = validate_interim_package(args.package_root)
        _print(asdict(result))
        return 0 if result.valid else 2

    if args.command == "migrate":
        if args.clean:
            _remove_database(args.database)
        store.migrate()
        _print(_status(store))
        return 0

    if args.command == "import":
        if not store.is_migrated():
            store.migrate()
        result = import_interim_package(
            store,
            args.package_root,
            max_records_per_split=args.max_records_per_split,
        )
        _print(asdict(result))
        return 0

    if args.command == "evaluate":
        report = evaluate_proxy_kpis(store)
        _print(report.to_dict())
        return 0 if report.proxy_research_completion else 2

    if args.command == "status":
        _print(_status(store))
        return 0

    if args.command == "bootstrap":
        if not store.is_migrated():
            store.migrate()
        _print(asdict(bootstrap_operational_evidence(store)))
        return 0

    if args.command == "retrain":
        _retrain(args.package_root, args.output_dir, small=args.small)
        result = validate_interim_package(args.output_dir)
        model_id = _register_retrain(store, args.output_dir) if store.is_migrated() else None
        _print(asdict(result) | {"registered_model_id": model_id})
        return 0 if result.valid else 2

    if args.command == "report":
        if not store.is_migrated():
            raise RuntimeError("interim_store_not_migrated")
        _print(asdict(_report(store, args.package_root)))
        return 0

    if args.command == "verify-release":
        result = verify_release(
            REPO_ROOT / "artifacts" / "tips" / "interim" / "evidence_manifest.json"
        )
        _print(result)
        return 0 if result["valid"] else 2

    if args.command == "all":
        store.migrate()
        if args.retrain:
            retrained = REPO_ROOT / "artifacts" / "tips" / "interim" / "retrained"
            _retrain(args.package_root, retrained, small=False)
            _register_retrain(store, retrained)
        imported = import_interim_package(store, args.package_root)
        bootstrap = bootstrap_operational_evidence(store)
        report = evaluate_proxy_kpis(store)
        release = _report(store, args.package_root)
        release_check = verify_release(
            REPO_ROOT / "artifacts" / "tips" / "interim" / "evidence_manifest.json"
        )
        result = {
            "import": asdict(imported),
            "bootstrap": asdict(bootstrap),
            "kpi": report.to_dict(),
            "release": asdict(release),
            "release_check": release_check,
        }
        _print(result)
        valid = report.proxy_research_completion and (
            not args.verify or bool(release_check["valid"])
        )
        return 0 if valid else 2

    raise AssertionError(f"unknown_command:{args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
