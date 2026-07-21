import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.chat.retrieval import (
    ChatQaEvalCase,
    RetrievalChunk,
    RetrievalCorpusManifest,
    evaluate_retrieval_hit_rate,
    load_chat_qa_eval_cases,
    load_retrieval_corpus_manifest,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build minimal counseling retrieval corpus and QA dataset D"
    )
    parser.add_argument(
        "--claims-jsonl",
        default="data/parsed_references/reference_claims_v1.jsonl",
        help="Parsed reference claims JSONL path",
    )
    parser.add_argument(
        "--reference-knowledge-json",
        default="data/knowledge/reference_knowledge_base_v1.json",
        help="Reference registry with source/effective-date lineage",
    )
    parser.add_argument(
        "--corpus-manifest-json",
        default="artifacts/retrieval/chat_retrieval_corpus_manifest_v1.json",
        help="Retrieval corpus manifest JSON path",
    )
    parser.add_argument(
        "--qa-dataset-jsonl",
        default="artifacts/datasets/chat_qa_dataset_d_v1.jsonl",
        help="QA dataset D JSONL path",
    )
    parser.add_argument(
        "--eval-report-json",
        default="artifacts/reports/chat_retrieval_eval_v1.json",
        help="Retrieval eval report JSON path",
    )
    parser.add_argument(
        "--eval-report-md",
        default="artifacts/reports/chat_retrieval_eval_v1.md",
        help="Retrieval eval report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    claims = _load_claim_rows(args.claims_jsonl)
    references = _load_reference_rows(args.reference_knowledge_json)
    chunks = [_build_chunk_from_claim(claim, references) for claim in claims]
    manifest = RetrievalCorpusManifest(
        manifest_version="chat_retrieval_corpus_manifest_v1",
        chunk_count=len(chunks),
        chunks=chunks,
    )
    qa_cases = [_build_eval_case_from_claim(claim) for claim in claims]
    eval_report = evaluate_retrieval_hit_rate(manifest, qa_cases, top_k=3)
    eval_report.update(
        {
            "corpus_manifest_path": args.corpus_manifest_json,
            "qa_dataset_path": args.qa_dataset_jsonl,
            "chunk_count": len(chunks),
            "qa_case_count": len(qa_cases),
        }
    )

    corpus_path = Path(args.corpus_manifest_json)
    qa_path = Path(args.qa_dataset_jsonl)
    eval_json_path = Path(args.eval_report_json)
    eval_md_path = Path(args.eval_report_md)
    for path in (corpus_path, qa_path, eval_json_path, eval_md_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    corpus_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    qa_path.write_text(
        "\n".join(case.model_dump_json() for case in qa_cases) + "\n",
        encoding="utf-8",
    )
    eval_json_path.write_text(
        json.dumps(eval_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    eval_md_path.write_text(_render_eval_markdown(eval_report), encoding="utf-8")

    # Read through loaders once so the next loop can attach answer/verifier without new wiring.
    load_retrieval_corpus_manifest(corpus_path)
    load_chat_qa_eval_cases(qa_path)

    print(
        json.dumps(
            {
                "corpus_manifest_json": str(corpus_path),
                "qa_dataset_jsonl": str(qa_path),
                "eval_report_json": str(eval_json_path),
                "chunk_count": len(chunks),
                "qa_case_count": len(qa_cases),
                "top1_hit_rate_pct": eval_report["top1_hit_rate_pct"],
                "topk_hit_rate_pct": eval_report["topk_hit_rate_pct"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_claim_rows(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_reference_rows(path: str | Path) -> dict[str, dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("references")
    if not isinstance(rows, list):
        raise ValueError("reference_registry_rows_required")
    references: dict[str, dict[str, object]] = {}
    for row in rows:
        reference_id = str(row.get("reference_id", ""))
        if not reference_id:
            raise ValueError("reference_registry_id_required")
        if reference_id in references:
            raise ValueError(f"duplicate_reference_registry_id:{reference_id}")
        references[reference_id] = row
    return references


def _build_chunk_from_claim(
    claim: dict[str, object], references: dict[str, dict[str, object]]
) -> RetrievalChunk:
    reference_id = str(claim["reference_id"])
    reference = references.get(reference_id)
    if reference is None:
        raise ValueError(f"claim_reference_not_registered:{reference_id}")
    identity_fields = ("source_title", "source_type", "page_or_section", "reference_uri")
    if any(claim[field] != reference[field] for field in identity_fields):
        raise ValueError(f"claim_reference_identity_mismatch:{reference_id}")
    parsed_source_uri = str(reference.get("parsed_source_uri", ""))
    parsed_source_path = (Path(__file__).resolve().parents[1] / parsed_source_uri).resolve()
    repository_root = Path(__file__).resolve().parents[1]
    if not parsed_source_uri or repository_root not in parsed_source_path.parents:
        raise ValueError(f"reference_parsed_source_path_invalid:{reference_id}")
    source_lines = parsed_source_path.read_text(encoding="utf-8").splitlines()
    line_start = int(claim["citation_span"]["line_start"])
    line_end = int(claim["citation_span"]["line_end"])
    if line_start < 1 or line_end < line_start or line_end > len(source_lines):
        raise ValueError(f"claim_source_line_range_invalid:{claim['claim_id']}")
    source_span = "\n".join(source_lines[line_start - 1 : line_end])
    if str(claim["claim_id"]) not in source_span or str(claim["claim_text"]) not in source_span:
        raise ValueError(f"claim_source_span_identity_mismatch:{claim['claim_id']}")
    excerpt = claim["citation_span"]["excerpt"]
    keywords = sorted(
        {
            claim["normalized_claim_type"],
            *claim.get("domain_keys", []),
            *claim.get("ingredient_keys", []),
            *claim.get("medication_keys", []),
        }
    )
    return RetrievalChunk(
        chunk_id=f"chunk::{claim['claim_id']}",
        reference_id=reference_id,
        claim_id=claim["claim_id"],
        source_title=claim["source_title"],
        source_type=claim["source_type"],
        page_or_section=claim["page_or_section"],
        reference_uri=claim["reference_uri"],
        parsed_source_uri=parsed_source_uri,
        license_status=reference["license_status"],
        effective_at=reference["effective_at"],
        retired_at=reference.get("retired_at"),
        line_start=line_start,
        line_end=line_end,
        normalized_claim_type=claim["normalized_claim_type"],
        text=claim["claim_text"],
        excerpt=excerpt,
        keywords=keywords,
        ingredient_keys=sorted(claim.get("ingredient_keys", [])),
        medication_keys=sorted(claim.get("medication_keys", [])),
        domain_keys=sorted(claim.get("domain_keys", [])),
    )


def _build_eval_case_from_claim(claim: dict[str, object]) -> ChatQaEvalCase:
    question, template_key, expected_terms = _question_template_for_claim(claim)
    return ChatQaEvalCase(
        case_id=f"chat-qa::{claim['claim_id']}",
        question=question,
        scope="supplement_counseling",
        answer_template_key=template_key,
        expected_chunk_ids=[f"chunk::{claim['claim_id']}"],
        expected_reference_ids=[claim["reference_id"]],
        expected_claim_ids=[claim["claim_id"]],
        expected_terms=expected_terms,
    )


def _question_template_for_claim(claim: dict[str, object]) -> tuple[str, str, list[str]]:
    claim_type = claim["normalized_claim_type"]
    ingredients = sorted(claim.get("ingredient_keys", []))
    medications = sorted(claim.get("medication_keys", []))
    if claim_type == "drug_interaction" and ingredients and medications:
        ingredient_text = " or ".join(ingredients)
        medication_text = " or ".join(medications)
        return (
            (
                "What should the counseling module say about "
                f"{ingredient_text} with {medication_text}?"
            ),
            "interaction_warning",
            ingredients + medications,
        )
    if claim_type == "citation_schema":
        return (
            "What citation fields should a counseling answer preserve for verifier-ready output?",
            "citation_schema_summary",
            ["ref_id", "source_title", "claim_text"],
        )
    if claim_type == "citation_requirement":
        return (
            "Why should the counseling module keep reference ids in its evidence-backed answer?",
            "citation_requirement_summary",
            ["reference_ids", "citation"],
        )
    if claim_type == "safety_recheck_policy":
        return (
            "How should a high-risk counseling path route when safety risk rises?",
            "safety_recheck_summary",
            ["trigger_safety_recheck"],
        )
    return (
        "What action-space constraint should the counseling module preserve in autonomous mode?",
        "action_space_summary",
        ["system-owned", "action space"],
    )


def _render_eval_markdown(report: dict[str, object]) -> str:
    lines = [
        "# chat retrieval eval v1",
        "",
        f"- corpus_manifest_path: `{report['corpus_manifest_path']}`",
        f"- qa_dataset_path: `{report['qa_dataset_path']}`",
        f"- chunk_count: `{report['chunk_count']}`",
        f"- qa_case_count: `{report['qa_case_count']}`",
        f"- top1_hit_rate_pct: `{report['top1_hit_rate_pct']}`",
        f"- topk_hit_rate_pct: `{report['topk_hit_rate_pct']}`",
        "",
        "## Cases",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['case_id']}`: top1_hit=`{case['top1_hit']}`, "
            f"topk_hit=`{case['topk_hit']}`, retrieved=`{case['retrieved_chunk_ids']}`"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
