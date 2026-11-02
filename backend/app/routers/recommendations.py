from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
from app.services.recommendation_service import RecommendationService
from app.middleware.auth_middleware import get_verified_user_id

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])
recommendation_service = RecommendationService()
from app.services.daily_drop_service import DailyDropService
daily_drop_service = DailyDropService()


class QuizSubmissionRequest(BaseModel):
    user_id: Optional[str] = None
    lesson_id: str
    answers: Dict[str, str]  # question index (as string or int) -> selected option string


class ContentActivityRequest(BaseModel):
    user_id: Optional[str] = None
    content_id: str


class RecommendationFeedbackPayload(BaseModel):
    lesson_id: str
    feedback: str  # 'like' | 'dislike' | 'irrelevant'
    lesson_title: Optional[str] = None
    reason: Optional[str] = None


@router.post("/feedback")
async def submit_lesson_feedback(payload: RecommendationFeedbackPayload, http_req: Request):
    user_id = get_verified_user_id(http_req)

    # If flagged as irrelevant or disliked with a reason, route directly to Admin Moderation Desk
    if payload.feedback == "irrelevant" or (payload.feedback == "dislike" and payload.reason):
        try:
            from app.routers.admin import _FLAGGED_ITEMS
            _FLAGGED_ITEMS.insert(0, {
                "id": f"flag-recom-{uuid.uuid4().hex[:8]}",
                "item_type": "recommendation",
                "sender_name": f"Learner ({user_id[:8]}...)",
                "target_context": f"Learning Sprint ({payload.lesson_title or payload.lesson_id})",
                "content_snippet": f"Lesson: {payload.lesson_title or payload.lesson_id}",
                "reason": payload.reason or "Learner reported this recommendation as irrelevant to their career roadmap.",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending_review",
            })
        except Exception as e:
            print(f"[recommendation-feedback] Moderation queue forward notice: {e}")

    return {
        "status": "success",
        "lesson_id": payload.lesson_id,
        "feedback": payload.feedback,
        "message": "Feedback recorded. Thank you for tuning the recommendation engine.",
    }



@router.get("/daily-drop/current")
async def get_current_daily_drop(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        drop = await daily_drop_service.get_or_create_daily_drop(caller_id)
        return {"status": "success", "drop": drop}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load daily drop: {str(e)}")


@router.post("/daily-drop/reroll")
async def reroll_daily_drop(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        drop = await daily_drop_service.reroll_daily_drop(caller_id)
        return {"status": "success", "drop": drop, "message": "Daily drop shuffled to secondary deficit."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reroll daily drop: {str(e)}")


@router.get("/library/completed")
async def get_user_completed_library(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        completed = await recommendation_service.get_completed_library_for_user(caller_id)
        return {"status": "success", "completed_library": completed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load completed library: {str(e)}")


@router.get("/{user_id}")
async def get_user_recommendations(
    user_id: str,
    request: Request,
    limit: int = 10,
    offset: int = 0,
    exclude_ids: Optional[List[str]] = None,
):
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
        raw_recommendations = await recommendation_service.get_recommendations_for_user(
            target_id, limit=limit + 5, offset=offset, exclude_ids=exclude_ids or []
        )
        completed_library = await recommendation_service.get_completed_library_for_user(target_id)
        completed_ids = {c.get("id") for c in completed_library if c.get("id")}
        recommendations = [
            r for r in raw_recommendations
            if not r.get("has_passed") and r.get("id") not in completed_ids
        ][:limit]
        return {
            "status": "success",
            "count": len(recommendations),
            "offset": offset,
            "limit": limit,
            "recommendations": recommendations,
            "completed_library": completed_library,
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
    return {"status": "success", "learning_status": "in_progress", "message": "Content open recorded"}


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

        if result.get("passed"):
            try:
                await daily_drop_service.record_lesson_passed(caller_id, request.lesson_id.strip())
            except Exception as ex:
                print(f"[daily-drop] Progress update notice: {ex}")

        return {
            "status": "success",
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")
