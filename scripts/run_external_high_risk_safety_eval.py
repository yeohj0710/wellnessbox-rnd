from __future__ import annotations

import argparse
import json
from pathlib import Path

from wellnessbox_rnd.evals.external_high_risk_safety import (
    ExternalHighRiskEvalContractError,
    run_external_high_risk_safety_eval,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a verified, independently labeled high-risk safety dataset."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--verification-receipt", type=Path, required=True)
    parser.add_argument("--coverage-protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = run_external_high_risk_safety_eval(
            dataset_path=args.dataset,
            attestation_path=args.attestation,
            verification_receipt_path=args.verification_receipt,
            coverage_protocol_path=args.coverage_protocol,
            output_path=args.output,
        )
    except ExternalHighRiskEvalContractError as error:
        print(json.dumps({"status": "INVALID_EXTERNAL_INPUT", "detail": str(error)}))
        return 2
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
