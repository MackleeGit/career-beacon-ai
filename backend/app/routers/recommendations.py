from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.recommendation_service import RecommendationService
from app.middleware.auth_middleware import get_verified_user_id

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])
recommendation_service = RecommendationService()


class QuizSubmissionRequest(BaseModel):
    user_id: Optional[str] = None
    lesson_id: str
    answers: Dict[str, str]  # question index (as string or int) -> selected option string


class ContentActivityRequest(BaseModel):
    user_id: Optional[str] = None
    content_id: str


@router.get("/{user_id}")
async def get_user_recommendations(user_id: str, request: Request, limit: int = 5, offset: int = 0):
    """
    Two-Stage Hybrid Recommendation Endpoint:
    1. Cryptographically verifies authenticated caller session.
    2. Database Coarse Filter: Extracts candidate lessons via pgvector similarity.
    3. Python Re-Ranker: Applies difficulty penalty, breadth boost, learning history, and source trust.
    4. Stable pagination with limit and offset.
    Returns the top curated micro-learning lessons for the caller's skill graph.
    """
    caller_id = get_verified_user_id(request)
    target_id = caller_id if user_id == "me" else user_id

    if target_id != caller_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot view another user's recommendations.",
        )

    try:
        recommendations = await recommendation_service.get_recommendations_for_user(target_id, limit=limit, offset=offset)
        return {
            "status": "success",
            "count": len(recommendations),
            "offset": offset,
            "limit": limit,
            "recommendations": recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.post("/activity/open")
async def record_content_open(request: ContentActivityRequest, http_req: Request):
    """Records that a learner opened a specific lesson resource."""
    caller_id = get_verified_user_id(http_req)
    if request.user_id and request.user_id != caller_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot record activity for another user.")
    recommendation_service.history_service.record_content_open(caller_id, request.content_id)
    return {"status": "success", "message": "Content open recorded"}


@router.post("/activity/complete")
async def record_content_complete(request: ContentActivityRequest, http_req: Request):
    """Records that a learner marked a specific lesson resource complete."""
    caller_id = get_verified_user_id(http_req)
    if request.user_id and request.user_id != caller_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot record activity for another user.")
    recommendation_service.history_service.record_content_completion(caller_id, request.content_id)
    return {"status": "success", "message": "Content completion recorded"}


@router.post("/submit-quiz")
async def submit_quiz(request: QuizSubmissionRequest, http_req: Request):
    """
    Validates user's quiz responses server-side:
    - Verifies caller session via JWT, preventing cross-user account tampering.
    - Validates answers against stored lesson answer key (server-side evaluation).
    - If passed (>= 60%), increments caller's user_skills proficiency (+10%, capped at 100%).
    - Auto-transitions to 'Mastered' at 100%.
    - If failed, provides an 'Ask MENTOR' suggestion.
    """
    caller_id = get_verified_user_id(http_req)

    # Prevent cross-user account tampering
    if request.user_id and request.user_id != caller_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot submit quiz on behalf of another user account.",
        )

    if not request.lesson_id or not request.lesson_id.strip():
        raise HTTPException(status_code=400, detail="Lesson ID is required.")

    try:
        # Convert string keys to int indices
        parsed_answers = {}
        for k, v in request.answers.items():
            try:
                parsed_answers[int(k)] = v
            except ValueError:
                parsed_answers[k] = v

        result = await recommendation_service.submit_quiz_answer(
            user_id=caller_id,
            lesson_id=request.lesson_id.strip(),
            answers=parsed_answers,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")
