"""
Focused test suite for Step 4: Assessment Integrity, Bounded Progression,
Repeated-Pass Farming Protection, and Evidence Hierarchy Preservation.

Covers:
  1. First pass awards +10% proficiency and upgrades self_reported -> quiz_verified.
  2. Repeated pass on same lesson awards 0% increment (farming prevented).
  3. Failing quiz awards 0% increment and triggers Ask MENTOR suggestion.
  4. Diagnostic assessment evidence is preserved (never downgraded to quiz_verified).
  5. Missing skill record in user profile is initialized with verified credit.
  6. Proficiency is strictly capped at 100%.
  7. Strict server-side evaluation against stored answer keys.
  8. Missing lesson or empty quiz handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def clean_attempt_store(tmp_path):
    """Provides an isolated temporary attempt store file."""
    test_file = str(tmp_path / "test_quiz_attempts.json")
    with patch("app.services.recommendation_service.ATTEMPTS_FILE", test_file), \
         patch("app.services.learning_history_service.ATTEMPTS_FILE", test_file):
        yield test_file


@pytest.fixture
def mock_lesson_with_quiz():
    """Returns a lesson dict with 5 validated questions and stored answers."""
    return {
        "id": "lesson-py-101",
        "title": "Python Basics",
        "associated_skill_id": "skill-python",
        "quizzes": [
            {
                "question": "What is Python?",
                "options": ["A snake", "A programming language", "A browser", "An OS"],
                "answer": "A programming language",
                "explanation": "Python is a high-level language."
            },
            {
                "question": "What is a list in Python?",
                "options": ["Mutable sequence", "Immutable set", "Database", "Function"],
                "answer": "Mutable sequence",
                "explanation": "Lists are mutable ordered collections."
            },
            {
                "question": "Which keyword defines a function?",
                "options": ["func", "def", "function", "fn"],
                "answer": "def",
                "explanation": "def is used in Python."
            },
            {
                "question": "What does len() return?",
                "options": ["Length of object", "Type of object", "Memory address", "Hash"],
                "answer": "Length of object",
                "explanation": "len() returns the number of items."
            },
            {
                "question": "What is PEP 8?",
                "options": ["A compiler", "Python style guide", "A package", "A database"],
                "answer": "Python style guide",
                "explanation": "PEP 8 is the official style guide."
            },
        ]
    }


@pytest.mark.asyncio
async def test_first_pass_increments_proficiency_and_upgrades_evidence(clean_attempt_store, mock_lesson_with_quiz):
    """Passing a quiz for the first time awards +10% and upgrades self_reported -> quiz_verified."""
    rec_service = RecommendationService()
    user_id = "user-1"
    lesson_id = mock_lesson_with_quiz["id"]
    skill_id = mock_lesson_with_quiz["associated_skill_id"]

    # User currently has 20% self_reported
    current_user_skill = {"proficiency": 20, "evidence_source": "self_reported"}
    update_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[current_user_skill])
                t.update = update_mock
            return t

        mock_sb.table.side_effect = table_router

        # 4 out of 5 correct = 80% (passing >= 60%)
        answers = {
            0: "A programming language",
            1: "Mutable sequence",
            2: "def",
            3: "Length of object",
            4: "Wrong answer",
        }

        result = await rec_service.submit_quiz_answer(user_id, lesson_id, answers)

        assert result["passed"] is True
        assert result["score"] == 4
        assert result["total"] == 5
        assert result["percentage"] == 80.0
        assert result["proficiency_increment"] == 10
        assert result["new_proficiency"] == 30
        assert result["already_completed"] is False

        # Verify DB update payload
        update_mock.assert_called_once()
        payload = update_mock.call_args[0][0]
        assert payload["proficiency"] == 30
        assert payload["evidence_source"] == "quiz_verified"


@pytest.mark.asyncio
async def test_repeated_pass_does_not_increment_proficiency(clean_attempt_store, mock_lesson_with_quiz):
    """Submitting the same passing quiz a second time awards 0% increment (farming prevented)."""
    rec_service = RecommendationService()
    user_id = "user-1"
    lesson_id = mock_lesson_with_quiz["id"]

    current_user_skill = {"proficiency": 30, "evidence_source": "quiz_verified"}
    update_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[current_user_skill])
                t.update = update_mock
            return t

        mock_sb.table.side_effect = table_router

        perfect_answers = {
            0: "A programming language",
            1: "Mutable sequence",
            2: "def",
            3: "Length of object",
            4: "Python style guide",
        }

        # First pass
        first_res = await rec_service.submit_quiz_answer(user_id, lesson_id, perfect_answers)
        assert first_res["passed"] is True
        assert first_res["proficiency_increment"] == 10
        assert first_res["new_proficiency"] == 40
        assert first_res["already_completed"] is False

        # Second pass (learner retakes same quiz)
        update_mock.reset_mock()
        second_res = await rec_service.submit_quiz_answer(user_id, lesson_id, perfect_answers)
        assert second_res["passed"] is True
        # Farming blocked: increment is 0, proficiency unchanged
        assert second_res["proficiency_increment"] == 0
        assert second_res["new_proficiency"] == 30
        assert second_res["already_completed"] is True

        payload = update_mock.call_args[0][0]
        assert payload["proficiency"] == 30  # No inflation!


@pytest.mark.asyncio
async def test_failing_quiz_does_not_increment_proficiency(clean_attempt_store, mock_lesson_with_quiz):
    """Score < 60% results in passed=False, 0% increment, and triggers Ask MENTOR suggestion."""
    rec_service = RecommendationService()
    user_id = "user-1"
    lesson_id = mock_lesson_with_quiz["id"]

    current_user_skill = {"proficiency": 25, "evidence_source": "self_reported"}
    update_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[current_user_skill])
                t.update = update_mock
            return t

        mock_sb.table.side_effect = table_router

        # 1 out of 5 correct = 20% (< 60% fail)
        failing_answers = {
            0: "A programming language",
            1: "Wrong",
            2: "Wrong",
            3: "Wrong",
            4: "Wrong",
        }

        result = await rec_service.submit_quiz_answer(user_id, lesson_id, failing_answers)

        assert result["passed"] is False
        assert result["score"] == 1
        assert result["percentage"] == 20.0
        assert result["proficiency_increment"] == 0
        assert result["new_proficiency"] == 25
        assert result["ask_mentor_suggested"] is True

        payload = update_mock.call_args[0][0]
        assert payload["proficiency"] == 25
        # Evidence source is NOT upgraded on failure
        assert "evidence_source" not in payload


@pytest.mark.asyncio
async def test_preserves_stronger_diagnostic_evidence(clean_attempt_store, mock_lesson_with_quiz):
    """
    Learner holds 'diagnostic_assessment' evidence.
    Passing a micro-quiz must NOT downgrade evidence_source to 'quiz_verified'.
    """
    rec_service = RecommendationService()
    user_id = "user-diagnostic"
    lesson_id = mock_lesson_with_quiz["id"]

    current_user_skill = {"proficiency": 50, "evidence_source": "diagnostic_assessment"}
    update_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[current_user_skill])
                t.update = update_mock
            return t

        mock_sb.table.side_effect = table_router

        passing_answers = {
            0: "A programming language",
            1: "Mutable sequence",
            2: "def",
            3: "Length of object",
        }

        result = await rec_service.submit_quiz_answer(user_id, lesson_id, passing_answers)

        assert result["passed"] is True
        assert result["new_proficiency"] == 60

        payload = update_mock.call_args[0][0]
        assert payload["proficiency"] == 60
        # Critical assertion: diagnostic_assessment evidence was preserved!
        assert "evidence_source" not in payload, "Must not overwrite stronger diagnostic evidence with quiz_verified"


@pytest.mark.asyncio
async def test_missing_skill_record_initialized_on_quiz_pass(clean_attempt_store, mock_lesson_with_quiz):
    """If user has no user_skills row for this lesson's skill, initialize record at 30% quiz_verified."""
    rec_service = RecommendationService()
    user_id = "user-new-skill"
    lesson_id = mock_lesson_with_quiz["id"]

    insert_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                # No existing skill row found
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                t.insert = insert_mock
            return t

        mock_sb.table.side_effect = table_router

        passing_answers = {
            0: "A programming language",
            1: "Mutable sequence",
            2: "def",
        }

        result = await rec_service.submit_quiz_answer(user_id, lesson_id, passing_answers)

        assert result["passed"] is True
        assert result["new_proficiency"] == 30
        assert result["proficiency_increment"] == 10

        insert_mock.assert_called_once()
        inserted_payload = insert_mock.call_args[0][0]
        assert inserted_payload["user_id"] == user_id
        assert inserted_payload["proficiency"] == 30
        assert inserted_payload["evidence_source"] == "quiz_verified"


@pytest.mark.asyncio
async def test_proficiency_strictly_capped_at_100(clean_attempt_store, mock_lesson_with_quiz):
    """Proficiency cannot exceed 100%, and skill_mastered is marked True."""
    rec_service = RecommendationService()
    user_id = "user-near-mastery"
    lesson_id = mock_lesson_with_quiz["id"]

    current_user_skill = {"proficiency": 95, "evidence_source": "quiz_verified"}
    update_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "micro_content":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_lesson_with_quiz])
            elif table_name == "quiz_attempts":
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[current_user_skill])
                t.update = update_mock
            return t

        mock_sb.table.side_effect = table_router

        passing_answers = {
            0: "A programming language",
            1: "Mutable sequence",
            2: "def",
        }

        result = await rec_service.submit_quiz_answer(user_id, lesson_id, passing_answers)

        assert result["passed"] is True
        assert result["new_proficiency"] == 100  # Capped at 100, not 105
        assert result["skill_mastered"] is True

        payload = update_mock.call_args[0][0]
        assert payload["proficiency"] == 100


@pytest.mark.asyncio
async def test_rejects_nonexistent_lesson_or_empty_quiz():
    """Returns clean error if lesson does not exist or has no active quiz."""
    rec_service = RecommendationService()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        # Case 1: Lesson not found
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        res1 = await rec_service.submit_quiz_answer("user-1", "non-existent-lesson", {})
        assert "error" in res1
        assert res1["error"] == "Lesson not found"

        # Case 2: Lesson has no active quizzes
        empty_quiz_lesson = {"id": "lesson-no-quiz", "title": "Empty Quiz Lesson", "quizzes": []}
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[empty_quiz_lesson])
        res2 = await rec_service.submit_quiz_answer("user-1", "lesson-no-quiz", {})
        assert "error" in res2
        assert res2["error"] == "This lesson does not have an active quiz."
