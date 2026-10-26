"""Step 6: End-to-end learner journey through onboarding, feed, quiz, and profile."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.routers.onboarding import SaveSkillsRequest, UnifiedSkillInput, get_onboarding_status, save_skills
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def isolated_journey_environment(tmp_path):
    """Give history persistence a fresh local store and prevent test-run leakage."""
    attempts_file = str(tmp_path / "journey_attempts.json")
    activity_file = str(tmp_path / "journey_activity.json")
    with open(attempts_file, "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(activity_file, "w", encoding="utf-8") as f:
        json.dump([], f)
    with patch("app.services.learning_history_service.ATTEMPTS_FILE", attempts_file), \
         patch("app.services.recommendation_service.ATTEMPTS_FILE", attempts_file), \
         patch("app.services.learning_history_service.ACTIVITY_FILE", activity_file), \
         patch("app.services.recommendation_service.ACTIVITY_FILE", activity_file):
        yield attempts_file, activity_file


@pytest.mark.asyncio
async def test_complete_learner_journey_and_feed_adaptation(isolated_journey_environment):
    user_id = "learner-sarah-journey"
    career_id = "career-fullstack-dev"
    career_title = "Full Stack Developer"
    career = {
        "id": career_id,
        "title": career_title,
        "description": "Builds web applications across frontend and backend systems.",
        "source_origin": "onet",
    }
    profile_store = {"id": user_id, "target_career_id": None}
    skill_catalog = {
        "skill-python": {"id": "skill-python", "name": "Python Programming", "category": "Core"},
        "skill-sql": {"id": "skill-sql", "name": "Relational Databases & SQL", "category": "Database"},
    }
    user_skills_store = []

    lesson_py = {
        "id": "lesson-py-fundamentals",
        "title": "Python Programming Fundamentals",
        "associated_skill_id": "skill-python",
        "difficulty_level": 2,
        "similarity": 0.92,
        "source_trust_score": 0.95,
        "quizzes": [
            {"question": "What is Python?", "options": ["A snake", "A programming language", "A browser", "An OS"], "answer": "A programming language", "explanation": "Python is a high-level programming language."},
            {"question": "Which keyword creates a function?", "options": ["func", "def", "function", "fn"], "answer": "def", "explanation": "def is used in Python."},
            {"question": "What is a list?", "options": ["Mutable sequence", "Immutable set", "Database", "Function"], "answer": "Mutable sequence", "explanation": "Lists are mutable ordered sequences."},
        ],
    }
    lesson_sql = {
        "id": "lesson-sql-fundamentals",
        "title": "SQL Query Basics & Joins",
        "associated_skill_id": "skill-sql",
        "difficulty_level": 2,
        "similarity": 0.88,
        "source_trust_score": 0.90,
        "quizzes": [],
    }
    candidates = [lesson_py, lesson_sql]
    rec_service = RecommendationService()
    history_service = rec_service.history_service

    with patch("app.services.recommendation_service.supabase_client") as rec_db, \
         patch("app.services.learning_history_service.supabase_client") as history_db, \
         patch("app.routers.onboarding.supabase_client") as onboarding_db, \
         patch("app.routers.onboarding.get_verified_user_id", return_value=user_id):
        # Keep history reads/writes on the isolated JSON stores, never a connected DB.
        history_db.table.side_effect = RuntimeError("Supabase disabled for isolated journey test")

        def onboarding_table_router(table_name):
            table = MagicMock()
            if table_name == "careers":
                def select_career(columns):
                    query = MagicMock()
                    result = {"source_origin": career["source_origin"]} if columns == "source_origin" else career
                    query.eq.return_value.execute.return_value = MagicMock(data=[result])
                    return query
                table.select.side_effect = select_career
            elif table_name == "profiles":
                table.select.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(
                    data=[dict(profile_store)] if profile_store["target_career_id"] else []
                )
                def update_profile(payload):
                    query = MagicMock()
                    query.eq.return_value.execute.side_effect = lambda: profile_store.update(payload)
                    return query
                table.update.side_effect = update_profile
            elif table_name == "user_skills":
                def upsert_skills(payload):
                    for incoming in payload:
                        existing = next((row for row in user_skills_store
                                         if row["user_id"] == incoming["user_id"]
                                         and row["skill_id"] == incoming["skill_id"]), None)
                        if existing:
                            existing.update(incoming)
                        else:
                            user_skills_store.append(dict(incoming))
                    return MagicMock()
                table.upsert.side_effect = upsert_skills
                table.select.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(
                    data=[{**row, "skills": skill_catalog[row["skill_id"]]}
                          for row in user_skills_store if row["user_id"] == user_id]
                )
            elif table_name == "career_skills":
                table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
                    {"skill_id": "skill-python", "importance": "essential", "importance_score": 0.9},
                    {"skill_id": "skill-sql", "importance": "essential", "importance_score": 0.9},
                ])
            return table

        onboarding_db.table.side_effect = onboarding_table_router

        def recommendation_table_router(table_name):
            table = MagicMock()
            if table_name == "profiles":
                table.select.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(
                    data=[dict(profile_store)] if profile_store["target_career_id"] else []
                )
            elif table_name == "careers":
                table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[career])
            elif table_name == "user_skills":
                table.select.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(
                    data=[{**row, "skills": skill_catalog[row["skill_id"]]}
                          for row in user_skills_store if row["user_id"] == user_id]
                )
                table.select.return_value.eq.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(
                    data=[row for row in user_skills_store
                          if row["user_id"] == user_id and row["skill_id"] == "skill-python"]
                )
                def update_skill(payload):
                    query = MagicMock()
                    def apply_update():
                        for row in user_skills_store:
                            if row["user_id"] == user_id and row["skill_id"] == "skill-python":
                                row.update(payload)
                        return MagicMock()
                    query.eq.return_value.eq.return_value.execute.side_effect = apply_update
                    return query
                table.update.side_effect = update_skill
            elif table_name == "career_skills":
                table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
                    {"skill_id": "skill-python", "importance": "essential", "importance_score": 0.9, "tier": 1},
                    {"skill_id": "skill-sql", "importance": "essential", "importance_score": 0.9, "tier": 1},
                ])
            elif table_name == "skill_dependencies":
                table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                table.select.return_value.execute.return_value = MagicMock(data=list(skill_catalog.values()))
            elif table_name == "micro_content":
                table.select.return_value.eq.return_value.execute.side_effect = lambda: MagicMock(data=[lesson_py])
            return table

        rec_db.table.side_effect = recommendation_table_router
        rec_db.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        # 1. Onboard through the real handler and confirm saved career/skill profile.
        request = MagicMock()
        result = await save_skills(
            SaveSkillsRequest(
                user_id=user_id,
                career_id=career_id,
                career_title=career_title,
                career_description=career["description"],
                skills=[
                    UnifiedSkillInput(skill_id="skill-python", name="Python Programming", category="Core", proficiency=20, importance="essential"),
                    UnifiedSkillInput(skill_id="skill-sql", name="Relational Databases & SQL", category="Database", proficiency=20, importance="essential"),
                ],
            ),
            request,
        )
        assert result["status"] == "success"
        assert profile_store["target_career_id"] == career_id
        assert len(user_skills_store) == 2
        assert all(row["evidence_source"] == "self_reported" for row in user_skills_store)

        status = await get_onboarding_status(user_id, request)
        assert status["onboarding_complete"] is True
        assert status["career"]["id"] == career_id
        assert {skill["id"] for skill in status["skills"]} == set(skill_catalog)

        # 2. Initial feed is personalized from the just-saved skill graph.
        initial_feed = await rec_service.get_recommendations_for_user(user_id, limit=2)
        assert [item["id"] for item in initial_feed] == [lesson_py["id"], lesson_sql["id"]]
        assert {item["associated_skill_id"] for item in initial_feed} == set(skill_catalog)
        assert all(item["has_passed"] is False for item in initial_feed)
        assert initial_feed[0]["user_current_proficiency"] == 20

        # 3. Opening the lesson is recorded against this learner and resource.
        history_service.record_content_open(user_id, lesson_py["id"])
        activity = history_service.get_user_activity_map(user_id)
        assert activity[lesson_py["id"]]["opened_at"] is not None

        # 4. A passing server-graded quiz advances only the associated skill.
        answers = {0: "A programming language", 1: "def", 2: "Mutable sequence"}
        quiz_result = await rec_service.submit_quiz_answer(user_id, lesson_py["id"], answers)
        assert quiz_result["passed"] is True
        assert quiz_result["score"] == quiz_result["total"] == 3
        assert quiz_result["proficiency_increment"] == 10
        assert quiz_result["new_proficiency"] == 30
        assert quiz_result["already_completed"] is False
        assert user_skills_store[0]["evidence_source"] == "quiz_verified"
        assert user_skills_store[0]["proficiency"] == 30
        assert user_skills_store[1]["proficiency"] == 20
        attempts = history_service.get_attempts_for_lesson(user_id, lesson_py["id"])
        assert len(attempts) == 1 and attempts[0]["attempt_number"] == 1

        # 5. The next feed prioritizes the other open career gap and retains review.
        updated_feed = await rec_service.get_recommendations_for_user(user_id, limit=2)
        assert updated_feed[0]["id"] == lesson_sql["id"]
        assert updated_feed[1]["id"] == lesson_py["id"]
        assert updated_feed[0]["relevance_score"] > updated_feed[1]["relevance_score"]
        assert updated_feed[1]["has_passed"] is True

        # 6. A retake is recorded but cannot inflate proficiency again.
        retake = await rec_service.submit_quiz_answer(user_id, lesson_py["id"], answers)
        assert retake["already_completed"] is True
        assert retake["proficiency_increment"] == 0
        assert retake["new_proficiency"] == 30
        attempts = history_service.get_attempts_for_lesson(user_id, lesson_py["id"])
        assert [attempt["attempt_number"] for attempt in attempts] == [1, 2]

        # There is no mentor matcher in this repository yet. Confirm the profile
        # contract it can consume, and that feed skills match the enrolled profile.
        assert all({"user_id", "skill_id", "proficiency", "evidence_source"} <= row.keys()
                   for row in user_skills_store)
        assert {row["skill_id"] for row in user_skills_store} == set(skill_catalog)
        assert all(0 <= row["proficiency"] <= 100 for row in user_skills_store)
        assert all(row["evidence_source"] in {"self_reported", "quiz_verified", "diagnostic_assessment"}
                   for row in user_skills_store)
