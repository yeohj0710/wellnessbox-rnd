from fastapi import APIRouter

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
def recommend_endpoint(payload: RecommendationRequest) -> RecommendationResponse:
    return recommend(payload)

