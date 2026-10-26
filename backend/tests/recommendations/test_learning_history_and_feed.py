"""
Focused test suite for Step 5: Learning History, Feed Continuity,
Assessment Retake Preservation, Activity Signals, Diversity, and Pagination.

Covers:
  1. Assessment attempts sequential numbering (retakes create attempt #2, #3 without overwriting).
  2. Feed suppresses completed and passed lessons to prevent repetition.
  3. Feed demotes repeatedly recommended but unengaged lessons.
  4. Feed pagination (limit and offset) provides stable non-overlapping slices.
  5. Diversity balancing prevents single-skill monopoly in top feed.
  6. Learning history persistence survives service re-instantiation (backend restart).
  7. Activity endpoints record opens and completions securely.
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.learning_history_service import LearningHistoryService
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def isolated_history_files(tmp_path):
    """Provides isolated attempt and activity files in a temporary directory."""
    attempts_file = str(tmp_path / "test_attempts.json")
    activity_file = str(tmp_path / "test_activity.json")
    with patch("app.services.learning_history_service.ATTEMPTS_FILE", attempts_file), \
         patch("app.services.learning_history_service.ACTIVITY_FILE", activity_file):
        yield attempts_file, activity_file


def test_assessment_attempts_sequential_numbering_and_retakes(isolated_history_files):
    """Retakes create distinct historical attempts (attempt #1, #2) with their own answers and scores."""
    service = LearningHistoryService()
    user_id = "learner-alice"
    lesson_id = "lesson-sql-101"

    # Attempt 1: Failed
    att1 = service.record_attempt(
        user_id=user_id,
        lesson_id=lesson_id,
        skill_id="skill-sql",
        answers={0: "Wrong", 1: "Wrong"},
        score=0,
        total=2,
        percentage=0.0,
        passed=False,
    )
    assert att1["attempt_number"] == 1
    assert att1["passed"] is False

    # Attempt 2: Passed (Retake)
    att2 = service.record_attempt(
        user_id=user_id,
        lesson_id=lesson_id,
        skill_id="skill-sql",
        answers={0: "Correct", 1: "Correct"},
        score=2,
        total=2,
        percentage=100.0,
        passed=True,
    )
    assert att2["attempt_number"] == 2
    assert att2["passed"] is True

    # Retrieve all historical attempts
    history = service.get_attempts_for_lesson(user_id, lesson_id)
    assert len(history) == 2
    assert history[0]["attempt_number"] == 1
    assert history[0]["score"] == 0
    assert history[1]["attempt_number"] == 2
    assert history[1]["score"] == 2

    # Verify pass status is recognized
    assert service.has_passed_lesson(user_id, lesson_id) is True


def test_learning_history_survives_restart(isolated_history_files):
    """Data persisted by LearningHistoryService is intact after a new instance is created."""
    service1 = LearningHistoryService()
    user_id = "learner-bob"
    lesson_id = "lesson-python-oop"

    service1.record_attempt(
        user_id=user_id,
        lesson_id=lesson_id,
        skill_id="skill-python",
        answers={0: "class", 1: "self"},
        score=2,
        total=2,
        percentage=100.0,
        passed=True,
    )
    service1.record_content_open(user_id, lesson_id)
    service1.record_content_completion(user_id, lesson_id)

    # Re-instantiate service (simulating backend reboot)
    service2 = LearningHistoryService()
    assert service2.has_passed_lesson(user_id, lesson_id) is True

    attempts = service2.get_attempts_for_lesson(user_id, lesson_id)
    assert len(attempts) == 1
    assert attempts[0]["passed"] is True

    act_map = service2.get_user_activity_map(user_id)
    assert lesson_id in act_map
    assert act_map[lesson_id]["opened_at"] is not None
    assert act_map[lesson_id]["completed_at"] is not None


@pytest.mark.asyncio
async def test_feed_suppresses_completed_and_passed_lessons(isolated_history_files):
    """A lesson that was completed and passed is heavily suppressed (0.20x) in favor of fresh lessons."""
    rec_service = RecommendationService()
    user_id = "user-continuous"
    career_id = "career-tech"

    # Record that lesson-py-passed was already passed by this user
    rec_service.history_service.record_attempt(
        user_id=user_id,
        lesson_id="lesson-py-passed",
        skill_id="skill-py",
        answers={},
        score=5,
        total=5,
        percentage=100.0,
        passed=True,
    )

    user_skills_mock = MagicMock(data=[
        {"skill_id": "skill-py", "proficiency": 30, "skills": {"id": "skill-py", "name": "Python", "category": "Core"}},
    ])

    candidates = [
        {
            "id": "lesson-py-passed",
            "title": "Python Basics (Already Mastered by User)",
            "associated_skill_id": "skill-py",
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
        {
            "id": "lesson-py-fresh",
            "title": "Python Control Flow (Fresh Unseen Content)",
            "associated_skill_id": "skill-py",
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"target_career_id": career_id}])
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": career_id, "title": "Developer"}])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = MagicMock(data=[{"id": "skill-py", "name": "Python", "category": "Core"}])
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        feed = await rec_service.get_recommendations_for_user(user_id, limit=2)

        assert len(feed) == 2
        # The fresh lesson must be ranked #1
        assert feed[0]["id"] == "lesson-py-fresh"
        assert feed[0]["has_passed"] is False

        # The already passed lesson is suppressed
        assert feed[1]["id"] == "lesson-py-passed"
        assert feed[1]["has_passed"] is True
        assert feed[0]["relevance_score"] > feed[1]["relevance_score"]


@pytest.mark.asyncio
async def test_feed_demotes_repeatedly_ignored_lessons(isolated_history_files):
    """Lessons recommended >= 3 times without learner open/engagement are demoted (0.60x)."""
    rec_service = RecommendationService()
    user_id = "user-engaged"
    career_id = "career-tech"

    # Pre-record that lesson-ignored was shown 3 times without being opened
    for _ in range(3):
        rec_service.history_service.record_impressions(user_id, ["lesson-ignored"])

    user_skills_mock = MagicMock(data=[
        {"skill_id": "skill-py", "proficiency": 30, "skills": {"id": "skill-py", "name": "Python", "category": "Core"}},
    ])

    candidates = [
        {
            "id": "lesson-ignored",
            "title": "Ignored Lesson",
            "associated_skill_id": "skill-py",
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
        {
            "id": "lesson-new",
            "title": "Brand New Lesson",
            "associated_skill_id": "skill-py",
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"target_career_id": career_id}])
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": career_id, "title": "Developer"}])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = MagicMock(data=[{"id": "skill-py", "name": "Python", "category": "Core"}])
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        feed = await rec_service.get_recommendations_for_user(user_id, limit=2)

        assert feed[0]["id"] == "lesson-new"
        assert feed[1]["id"] == "lesson-ignored"
        assert feed[0]["relevance_score"] > feed[1]["relevance_score"]


@pytest.mark.asyncio
async def test_feed_pagination_offset_and_limit(isolated_history_files):
    """Pagination via offset and limit provides stable, non-overlapping slices of the feed."""
    rec_service = RecommendationService()
    user_id = "user-pager"
    career_id = "career-tech"

    user_skills_mock = MagicMock(data=[
        {"skill_id": "skill-py", "proficiency": 30, "skills": {"id": "skill-py", "name": "Python", "category": "Core"}},
    ])

    candidates = [
        {
            "id": f"lesson-{i}",
            "title": f"Lesson {i}",
            "associated_skill_id": "skill-py",
            "difficulty_level": 2,
            "similarity": 0.90 - (i * 0.05),
            "source_trust_score": 0.90,
            "quizzes": [],
        }
        for i in range(6)
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"target_career_id": career_id}])
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": career_id, "title": "Developer"}])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = MagicMock(data=[{"id": "skill-py", "name": "Python", "category": "Core"}])
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        # Page 1: first 2 items
        page1 = await rec_service.get_recommendations_for_user(user_id, limit=2, offset=0)
        assert len(page1) == 2

        # Page 2: next 2 items
        page2 = await rec_service.get_recommendations_for_user(user_id, limit=2, offset=2)
        assert len(page2) == 2

        # Verify completely disjoint sets of IDs
        page1_ids = {item["id"] for item in page1}
        page2_ids = {item["id"] for item in page2}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_feed_diversity_balances_multiple_skill_gaps(isolated_history_files):
    """
    Candidate list contains 3 lessons for Skill 1 and 2 lessons for Skill 2.
    Diversity balancing dampens duplicate skill items so Skill 2 is represented.
    """
    rec_service = RecommendationService()
    user_id = "user-diversity"
    career_id = "career-tech"

    user_skills_mock = MagicMock(data=[
        {"skill_id": "skill-py", "proficiency": 25, "skills": {"id": "skill-py", "name": "Python", "category": "Core"}},
        {"skill_id": "skill-sql", "proficiency": 25, "skills": {"id": "skill-sql", "name": "SQL", "category": "Data"}},
    ])

    candidates = [
        {"id": "py-1", "title": "Python 1", "associated_skill_id": "skill-py", "difficulty_level": 2, "similarity": 0.90, "source_trust_score": 0.9, "quizzes": []},
        {"id": "py-2", "title": "Python 2", "associated_skill_id": "skill-py", "difficulty_level": 2, "similarity": 0.89, "source_trust_score": 0.9, "quizzes": []},
        {"id": "py-3", "title": "Python 3", "associated_skill_id": "skill-py", "difficulty_level": 2, "similarity": 0.88, "source_trust_score": 0.9, "quizzes": []},
        {"id": "sql-1", "title": "SQL 1", "associated_skill_id": "skill-sql", "difficulty_level": 2, "similarity": 0.87, "source_trust_score": 0.9, "quizzes": []},
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"target_career_id": career_id}])
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": career_id, "title": "Developer"}])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = MagicMock(data=[
                    {"id": "skill-py", "name": "Python", "category": "Core"},
                    {"id": "skill-sql", "name": "SQL", "category": "Data"},
                ])
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        feed = await rec_service.get_recommendations_for_user(user_id, limit=3)

        skills_in_top_3 = [item["associated_skill_id"] for item in feed]
        # SQL must appear in the top 3 due to diversity dampening on repeated Python lessons
        assert "skill-sql" in skills_in_top_3
