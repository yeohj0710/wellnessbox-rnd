from fastapi.testclient import TestClient

from apps.inference_api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "wellnessbox-rnd"


def test_recommend_endpoint_returns_structured_response() -> None:
    payload = {
        "user_profile": {
            "age": 34,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["stress_support", "sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "medications": [],
        "current_supplements": [],
        "lifestyle": {
            "sleep_hours": 5.5,
            "stress_level": 4,
            "activity_level": "lightly_active",
            "smoker": False,
            "alcohol_per_week": 1,
        },
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": True,
            "cgm": False,
            "genetic": False,
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }

    response = client.post("/v1/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["next_action"] == "start_plan"
    assert len(body["recommendations"]) >= 1
    assert body["decision_summary"]["headline"] == "deterministic baseline result"
    assert body["next_action_rationale"]["reason_code"] == "start_plan_ready"
    assert "safety_summary" in body
    assert "safety_evidence" in body
    assert "follow_up_questions" in body
    assert "limitation_details" in body
    assert "metadata" in body


def test_recommend_endpoint_marks_review_when_warfarin_is_present() -> None:
    payload = {
        "user_profile": {
            "age": 61,
            "biological_sex": "male",
            "pregnant": False,
        },
        "goals": ["heart_health"],
        "symptoms": [],
        "conditions": [],
        "medications": [{"name": "warfarin", "dose": "5mg"}],
        "current_supplements": [],
        "lifestyle": {
            "sleep_hours": 7,
            "stress_level": 2,
            "activity_level": "moderately_active",
            "smoker": False,
            "alcohol_per_week": 0,
        },
        "input_availability": {
            "survey": True,
            "nhis": True,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }

    response = client.post("/v1/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["next_action"] == "collect_more_input"
    assert (
        body["next_action_rationale"]["reason_code"]
        == "collect_more_input_multiple_missing_items"
    )
    assert [item["ingredient_key"] for item in body["recommendations"]] == ["coq10"]
    assert "omega3" in body["safety_summary"]["excluded_ingredients"]
    assert any(item["code"] == "SAFETY-ANTICOAG-001" for item in body["safety_evidence"])
    assert body["decision_summary"]["headline"] == "deterministic baseline result"


def test_recommend_endpoint_blocks_when_survey_input_is_missing() -> None:
    payload = {
        "user_profile": {
            "age": 45,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["general_wellness"],
        "symptoms": [],
        "conditions": [],
        "medications": [],
        "current_supplements": [],
        "lifestyle": {
            "sleep_hours": 6.5,
            "stress_level": 3,
            "activity_level": "sedentary",
            "smoker": False,
            "alcohol_per_week": 2,
        },
        "input_availability": {
            "survey": False,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "preferences": {
            "budget_level": "low",
            "max_products": 1,
            "avoid_ingredients": [],
        },
    }

    response = client.post("/v1/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["next_action"] == "collect_more_input"
    assert (
        body["next_action_rationale"]["reason_code"]
        == "collect_more_input_high_priority_missing_info"
    )
    assert [item["ingredient_key"] for item in body["recommendations"]] == ["vitamin_d3"]
    assert any(item["code"] == "missing_survey" for item in body["missing_information"])
