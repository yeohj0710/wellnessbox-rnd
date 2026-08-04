from __future__ import annotations

from pathlib import Path

from wellnessbox_rnd.evals.reference_standard import load_contract, seal_reference_standard
from wellnessbox_rnd.evals.sealed_kpi_measurement import (
    generate_kpi1_engine_outputs,
    generate_kpi3_engine_outputs,
    generate_kpi4_engine_outputs,
    generate_kpi5_engine_outputs,
    kpi1_request_from_prompt,
    kpi3_event_from_prompt,
    kpi5_request_from_prompt,
    run_kpi3_measurement,
)
from wellnessbox_rnd.interim.next_action import NextAction

ROOT = Path(__file__).resolve().parents[1]


def _seal(cases):
    return seal_reference_standard(
        indicator_id="KPI-3",
        cases=cases,
        sealed_by="등록 검토자",
        sealed_at="2026-08-04T00:00:00Z",
        contract=load_contract(ROOT),
        provenance={
            "role_separation": {
                "system_under_test_id": "wellnessbox-next-action-engine-v1"
            }
        },
    )


def test_kpi3_prompt_translation_maps_semantics_not_answer_labels() -> None:
    event = kpi3_event_from_prompt("관찰: 복용 후 두드러기가 올라왔다고 보고했다")

    assert event["adverse_event"] is True
    assert "stop_and_escalate" not in event.values()


def test_kpi1_prompt_translation_builds_structured_request_without_answers() -> None:
    request = kpi1_request_from_prompt(
        "영역 대사 및 순환 6. 당독소(AGEs) 관리 / 판정 「1. 생성 억제 (당화 차단)」 "
        "/ 나이 28 / 복용약 Amlodipine"
    )

    assert request.user_profile.age == 28
    assert request.goals[0].value == "blood_glucose"
    assert [item.name for item in request.medications] == ["Amlodipine"]


def test_kpi1_engine_output_generation_does_not_take_an_answer_key() -> None:
    outputs = generate_kpi1_engine_outputs(
        [
            {
                "case_id": "case-1",
                "prompt": (
                    "영역 대사 및 순환 6. 당독소(AGEs) 관리 / 판정 「1. 생성 억제 (당화 차단)」 "
                    "/ 나이 28 / 복용약 없음"
                ),
            }
        ]
    )

    assert outputs["case-1"]["actual_answer"]
    assert outputs["case-1"]["execution_success"] is True


def test_kpi5_prompt_translation_extracts_mode_without_answer_labels() -> None:
    request, mode, medication, ingredient = kpi5_request_from_prompt(
        "Esomeprazole 복용자 상담에서 magnesium_glycinate 관계의 라벨과 원문 근거를 함께 제시하면?"
    )

    assert mode == "combined"
    assert medication == "Esomeprazole"
    assert ingredient == "magnesium_glycinate"
    assert request.medications[0].name == "Esomeprazole"
    assert request.current_supplements[0].ingredients[0].name == "magnesium_glycinate"


def test_kpi5_engine_output_generation_records_only_safety_engine_fields() -> None:
    outputs = generate_kpi5_engine_outputs(
        [
            {
                "case_id": "case-1",
                "prompt": "Atorvastatin 복용자에게 coq10 는 어떤 관계인가?",
            }
        ]
    )

    assert outputs["case-1"]["actual_answer"] == []
    assert outputs["case-1"]["actual_label"] is None
    assert outputs["case-1"]["actual_evidence"] is None
    assert outputs["case-1"]["execution_success"] is True
    assert outputs["case-1"]["postcondition_success"] is True


def test_kpi4_engine_output_generation_uses_chat_adapter_without_live_api() -> None:
    outputs = generate_kpi4_engine_outputs(
        [
            {
                "case_id": "case-1",
                "prompt": "Esomeprazole 복용자에게 calcium_citrate 는 어떤 관계인가?",
            }
        ]
    )

    assert outputs["case-1"]["provider"] == "deterministic_template_fallback"
    assert outputs["case-1"]["fallback_reason"] == "live_api_disabled"
    assert outputs["case-1"]["actual_answer"] == []
    assert outputs["case-1"]["execution_success"] is True
    assert outputs["case-1"]["postcondition_success"] is True


def test_kpi3_prompt_translation_ignores_signal_words_in_the_goal() -> None:
    event = kpi3_event_from_prompt(
        "목표 두드러기 관리 / 관찰: 복용 8주차인데 목표 지표가 오히려 나빠졌다"
    )

    assert event["adverse_event"] is False
    assert event["score_delta"] == -0.1


def test_kpi3_engine_output_generation_does_not_take_an_answer_key() -> None:
    outputs = generate_kpi3_engine_outputs(
        [
            {
                "case_id": "case-1",
                "prompt": "관찰: 목표 지표가 개선됐고 불편 호소는 없다",
            }
        ]
    )

    assert outputs["case-1"]["actual_action"] == [NextAction.MAINTAIN.value]
    assert outputs["case-1"]["execution_success"] is True
    assert outputs["case-1"]["postcondition_success"] is True


def test_kpi3_measurement_checks_action_execution_and_postcondition() -> None:
    cases = {
        "case-1": [NextAction.STOP_AND_ESCALATE.value],
        "case-2": [NextAction.MAINTAIN.value],
    }
    seal = _seal(cases)
    drafts = [
        {
            "case_id": "case-1",
            "prompt": "관찰: 복용 후 두드러기가 올라왔다고 보고했다",
        },
        {
            "case_id": "case-2",
            "prompt": "관찰: 목표 지표가 개선됐고 불편 호소는 없다",
        },
    ]

    result = run_kpi3_measurement(
        seal=seal,
        drafts=drafts,
        measured_at="2026-08-04T01:00:00Z",
    )

    assert result["case_count"] == 2
    assert result["correct_count"] == 2
    assert result["accuracy_pct"] == 100.0
    assert result["execution_failure_count"] == 0
    assert result["postcondition_failure_count"] == 0
    assert result["measurement_environment"] == "research_phase_internal_measurement"
    assert len(result["input_adapter_sha256"]) == 64
    assert len(result["engine_artifacts"]) == 3


def test_kpi3_measurement_refuses_prompt_case_mismatch() -> None:
    seal = _seal({"case-1": [NextAction.MAINTAIN.value]})

    try:
        run_kpi3_measurement(
            seal=seal,
            drafts=[{"case_id": "case-2", "prompt": "목표 지표가 개선됐고"}],
        )
    except ValueError as exc:
        assert str(exc) == "kpi3_prompt_and_seal_case_ids_mismatch"
    else:
        raise AssertionError("case mismatch must be rejected")
