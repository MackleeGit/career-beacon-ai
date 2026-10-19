from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])
recommendation_service = RecommendationService()


class QuizSubmissionRequest(BaseModel):
    user_id: str
    lesson_id: str
    answers: Dict[str, str]  # question index (as string or int) -> selected option string


@router.get("/{user_id}")
async def get_user_recommendations(user_id: str, limit: int = 5):
    """
    Two-Stage Hybrid Recommendation Endpoint:
    1. Database Coarse Filter: Extracts 30 candidate lessons via pgvector similarity.
    2. Python Re-Ranker: Applies difficulty penalty, breadth boost, and source trust multiplier.
    Returns the top curated micro-learning lessons for the user's skill graph.
    """
    try:
        recommendations = await recommendation_service.get_recommendations_for_user(user_id, limit=limit)
        return {
            "status": "success",
            "count": len(recommendations),
            "recommendations": recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.post("/submit-quiz")
async def submit_quiz(request: QuizSubmissionRequest):
    """
    Validates user's quiz responses:
    - Provides immediate pedagogical explanations per question.
    - If passed (>= 60%), increments user_skills proficiency by +10% (capped at 100%).
    - Auto-transitions to 'Mastered' at 100%.
    - If failed, provides an 'Ask MENTOR' suggestion.
    """
    try:
        # Convert string keys to int indices
        parsed_answers = {}
        for k, v in request.answers.items():
            try:
                parsed_answers[int(k)] = v
            except ValueError:
                parsed_answers[k] = v

        result = await recommendation_service.submit_quiz_answer(
            user_id=request.user_id,
            lesson_id=request.lesson_id,
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
