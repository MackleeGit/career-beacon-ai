import pytest
from starlette.testclient import TestClient
from starlette.requests import Request
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.main import app
from app.routers.recommendations import get_user_recommendations, submit_quiz, QuizSubmissionRequest

client = TestClient(app)


def test_unauthenticated_recommendations_rejected():
    """Verify unauthenticated GET /api/recommendations/{user_id} returns 401."""
    res = client.get("/api/recommendations/some-user-uuid")
    assert res.status_code == 401
    assert "Authorization" in res.json().get("detail", "")


def test_unauthenticated_quiz_submission_rejected():
    """Verify unauthenticated POST /api/recommendations/submit-quiz returns 401."""
    res = client.post("/api/recommendations/submit-quiz", json={
        "user_id": "some-user-uuid",
        "lesson_id": "some-lesson-uuid",
        "answers": {"0": "A"}
    })
    assert res.status_code == 401
    assert "Authorization" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_cross_user_recommendations_forbidden():
    """Verify user A cannot access user B's personalized recommendations."""
    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "authenticated-user-a"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_recommendations(user_id="target-user-b", request=mock_req)

    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_own_recommendations_authorized():
    """Verify user can access their own recommendations (or using 'me')."""
    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "authenticated-user-a"}

    with patch("app.routers.recommendations.recommendation_service.get_recommendations_for_user") as mock_get_recs:
        mock_get_recs.return_value = [{"id": "lesson-1", "title": "Intro to Git"}]

        # Test explicit own user_id
        res = await get_user_recommendations(user_id="authenticated-user-a", request=mock_req)
        assert res["status"] == "success"
        assert len(res["recommendations"]) == 1

        # Test 'me' alias
        res_me = await get_user_recommendations(user_id="me", request=mock_req)
        assert res_me["status"] == "success"
        assert len(res_me["recommendations"]) == 1


@pytest.mark.asyncio
async def test_cross_user_quiz_submission_forbidden():
    """Verify user A cannot submit a quiz on behalf of user B to alter their proficiency."""
    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "authenticated-user-a"}

    payload = QuizSubmissionRequest(
        user_id="target-user-b",
        lesson_id="lesson-123",
        answers={"0": "Option A"}
    )

    with pytest.raises(HTTPException) as exc_info:
        await submit_quiz(request=payload, http_req=mock_req)

    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_quiz_submission_uses_authenticated_user_id():
    """Verify that submit_quiz delegates strictly to authenticated caller ID."""
    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "authenticated-user-a"}

    payload = QuizSubmissionRequest(
        user_id="authenticated-user-a",
        lesson_id="lesson-123",
        answers={"0": "Option A"}
    )

    with patch("app.routers.recommendations.recommendation_service.submit_quiz_answer") as mock_submit:
        mock_submit.return_value = {
            "passed": True,
            "score": 1,
            "total": 1,
            "percentage": 100.0,
            "proficiency_increment": 10,
            "new_proficiency": 60,
            "skill_mastered": False,
            "ask_mentor_suggested": False,
            "feedback": [],
        }

        res = await submit_quiz(request=payload, http_req=mock_req)
        assert res["status"] == "success"
        assert res["passed"] is True

        # Ensure recommendation_service was called with authenticated caller ID
        mock_submit.assert_called_once_with(
            user_id="authenticated-user-a",
            lesson_id="lesson-123",
            answers={0: "Option A"}
        )
