"""
Focused test suite for Step 3: Candidate Retrieval, Skill Graph DAG Signals,
Career Metadata Weighting, and Pedagogical Ranking.

Covers:
  1. Relational fallback targets enrolled skills (no arbitrary first-30 rows).
  2. Prerequisite direction: Skill B requires A -> weak A penalizes B, not A; A gets unblocking boost.
  3. Missing prerequisite record vs verified low proficiency (<60%).
  4. Career graph importance (essential / Tier 1 vs optional).
  5. Mastered skill deprioritization without total exclusion.
  6. Semantic relevance preservation (irrelevant content penalized).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def base_user_setup():
    """Sets up mock user profile and skills."""
    user_id = "user-123"
    career_id = "career-456"

    profile_mock = MagicMock()
    profile_mock.data = [{"target_career_id": career_id}]

    career_mock = MagicMock()
    career_mock.data = [{"id": career_id, "title": "Software Engineer", "description": "Tech career"}]

    return user_id, career_id, profile_mock, career_mock


@pytest.mark.asyncio
async def test_relational_fallback_targets_enrolled_skills_not_arbitrary(base_user_setup):
    """When vector RPC yields 0 candidates, fallback queries ONLY the learner's enrolled skills."""
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_id_1 = "skill-python"
    skill_id_2 = "skill-sql"

    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_id_1, "proficiency": 25, "skills": {"id": skill_id_1, "name": "Python", "category": "Core"}},
        {"skill_id": skill_id_2, "proficiency": 30, "skills": {"id": skill_id_2, "name": "SQL", "category": "Data"}},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [
        {"id": skill_id_1, "name": "Python", "category": "Core"},
        {"id": skill_id_2, "name": "SQL", "category": "Data"},
    ]

    # Mock micro_content query table
    table_query_mock = MagicMock()
    in_filter_mock = MagicMock()
    limit_mock = MagicMock()

    candidate_items = [
        {
            "id": "lesson-py-1",
            "title": "Python Control Flow",
            "associated_skill_id": skill_id_1,
            "difficulty_level": 2,
            "source_trust_score": 0.9,
            "quizzes": [],
            "source_url": "https://docs.python.org",
        }
    ]
    limit_mock.execute.return_value = MagicMock(data=candidate_items)
    in_filter_mock.limit.return_value = limit_mock
    table_query_mock.select.return_value.in_.return_value = in_filter_mock

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            elif table_name == "micro_content":
                return table_query_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=[])  # RPC returns empty

        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)
        rec_service.content_service.generate_dynamic_lesson_for_skill = AsyncMock(return_value=None)

        results = await rec_service.get_recommendations_for_user(user_id, limit=2)

        # Verify relational fallback queried .in_("associated_skill_id", ...)
        table_query_mock.select.return_value.in_.assert_called_once()
        call_args = table_query_mock.select.return_value.in_.call_args
        assert call_args[0][0] == "associated_skill_id"
        queried_skills = set(call_args[0][1])
        assert queried_skills == {skill_id_1, skill_id_2}
        # Association scopes fallback candidates but is not semantic evidence.
        assert results == []


@pytest.mark.asyncio
async def test_prerequisite_direction_penalizes_dependent_not_prerequisite(base_user_setup):
    """
    Skill B requires Prerequisite A.
    Learner has low proficiency in A (30% < 60%).
    Result:
      - Skill B incurs prerequisite penalty (0.50).
      - Skill A does NOT incur penalty (1.0) and receives unblocking boost (1.15).
      - Skill A ranks significantly higher than Skill B.
    """
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_a = "skill-python-basics"
    skill_b = "skill-asyncio-concurrency"

    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_a, "proficiency": 30, "skills": {"id": skill_a, "name": "Python Basics", "category": "Core"}},
        {"skill_id": skill_b, "proficiency": 20, "skills": {"id": skill_b, "name": "AsyncIO", "category": "Advanced"}},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [
        {"id": skill_a, "name": "Python Basics", "category": "Core"},
        {"id": skill_b, "name": "AsyncIO", "category": "Advanced"},
    ]

    # Skill B requires Skill A
    deps_mock = MagicMock(data=[
        {"skill_id": skill_b, "prerequisite_id": skill_a, "relationship_type": "requires"}
    ])

    candidates = [
        {
            "id": "lesson-b",
            "title": "Advanced AsyncIO Streams",
            "associated_skill_id": skill_b,
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.9,
            "quizzes": [],
        },
        {
            "id": "lesson-a",
            "title": "Python Control Flow & Functions",
            "associated_skill_id": skill_a,
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.9,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = deps_mock
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)

        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        results = await rec_service.get_recommendations_for_user(user_id, limit=2)

        assert len(results) == 2
        # Skill A must be ranked #1 because Skill B has an unmet prerequisite
        assert results[0]["associated_skill_id"] == skill_a
        assert results[0]["has_unmet_prerequisites"] is False
        assert results[0]["is_unblocking"] is True

        assert results[1]["associated_skill_id"] == skill_b
        assert results[1]["has_unmet_prerequisites"] is True
        assert results[1]["relevance_score"] < results[0]["relevance_score"]


@pytest.mark.asyncio
async def test_missing_prerequisite_record_distinguished_from_verified_zero(base_user_setup):
    """
    Distinguishes an unassessed prerequisite (no profile row) from confirmed low proficiency.
    An unassessed prerequisite applies a mild uncertainty discount (0.85),
    scoring higher than a confirmed failing prerequisite (<60%, 0.50).
    """
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_target = "skill-cloud-deployment"
    skill_prereq_unassessed = "skill-docker-basics"
    skill_prereq_failed = "skill-linux-basics"

    # User only has a record for skill_target (25%) and skill_prereq_failed (20%).
    # skill_prereq_unassessed has NO record.
    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_target, "proficiency": 25, "skills": {"id": skill_target, "name": "Cloud Deployment", "category": "DevOps"}},
        {"skill_id": skill_prereq_failed, "proficiency": 20, "skills": {"id": skill_prereq_failed, "name": "Linux", "category": "DevOps"}},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [
        {"id": skill_target, "name": "Cloud Deployment", "category": "DevOps"},
        {"id": skill_prereq_unassessed, "name": "Docker Basics", "category": "DevOps"},
        {"id": skill_prereq_failed, "name": "Linux", "category": "DevOps"},
    ]

    candidates = [
        {
            "id": "lesson-target",
            "title": "Cloud Infrastructure",
            "associated_skill_id": skill_target,
            "difficulty_level": 2,
            "similarity": 0.80,
            "source_trust_score": 0.9,
            "quizzes": [],
        }
    ]

    deps_table_mock = MagicMock()

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                return deps_table_mock
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        # Case 1: Target requires UNASSESSED prerequisite (learner has no record for docker)
        deps_unassessed = MagicMock(data=[
            {"skill_id": skill_target, "prerequisite_id": skill_prereq_unassessed, "relationship_type": "requires"}
        ])
        deps_table_mock.select.return_value.in_.return_value.execute.return_value = deps_unassessed
        res_unassessed = await rec_service.get_recommendations_for_user(user_id, limit=1)

        # Case 2: Target requires CONFIRMED FAILING prerequisite (learner has 20% in linux)
        deps_failed = MagicMock(data=[
            {"skill_id": skill_target, "prerequisite_id": skill_prereq_failed, "relationship_type": "requires"}
        ])
        deps_table_mock.select.return_value.in_.return_value.execute.return_value = deps_failed
        res_failed = await rec_service.get_recommendations_for_user(user_id, limit=1)

        # The unassessed prerequisite must receive a higher score than the verified failing one
        assert res_unassessed[0]["relevance_score"] > res_failed[0]["relevance_score"]
        # The unassessed case does not flag has_unmet_prerequisites as True (which is reserved for verified low proficiency)
        assert res_unassessed[0]["has_unmet_prerequisites"] is False
        assert res_failed[0]["has_unmet_prerequisites"] is True


@pytest.mark.asyncio
async def test_career_importance_prioritizes_essential_over_optional(base_user_setup):
    """
    Two skills with identical proficiency (20%) and similarity (0.80).
    Skill X is marked 'essential' (Tier 1).
    Skill Y is marked 'optional' (Tier 3).
    Skill X must score higher and rank first.
    """
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_x = "skill-essential"
    skill_y = "skill-optional"

    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_x, "proficiency": 20, "skills": {"id": skill_x, "name": "Essential Architecture", "category": "Core"}},
        {"skill_id": skill_y, "proficiency": 20, "skills": {"id": skill_y, "name": "Optional Tooling", "category": "Tools"}},
    ]

    career_skills_mock = MagicMock()
    career_skills_mock.data = [
        {"skill_id": skill_x, "importance": "essential", "tier": 1, "importance_score": 0.95},
        {"skill_id": skill_y, "importance": "optional", "tier": 3, "importance_score": 0.20},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [
        {"id": skill_x, "name": "Essential Architecture", "category": "Core"},
        {"id": skill_y, "name": "Optional Tooling", "category": "Tools"},
    ]

    candidates = [
        {
            "id": "lesson-y",
            "title": "Optional Tooling Guide",
            "associated_skill_id": skill_y,
            "difficulty_level": 2,
            "similarity": 0.80,
            "source_trust_score": 0.9,
            "quizzes": [],
        },
        {
            "id": "lesson-x",
            "title": "Essential Architecture Patterns",
            "associated_skill_id": skill_x,
            "difficulty_level": 2,
            "similarity": 0.80,
            "source_trust_score": 0.9,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = career_skills_mock
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        results = await rec_service.get_recommendations_for_user(user_id, limit=2)

        assert len(results) == 2
        assert results[0]["associated_skill_id"] == skill_x
        assert results[1]["associated_skill_id"] == skill_y
        assert results[0]["career_importance"] == "essential"
        assert results[0]["relevance_score"] > results[1]["relevance_score"]


@pytest.mark.asyncio
async def test_mastered_skill_deprioritized_without_complete_exclusion(base_user_setup):
    """
    Skill with 100% proficiency is deprioritized relative to a 20% gap skill,
    but is NOT excluded or zeroed out, retaining revision/extension potential.
    """
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_gap = "skill-gap-data"
    skill_mastered = "skill-mastered-python"

    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_gap, "proficiency": 20, "skills": {"id": skill_gap, "name": "Data Pipelines", "category": "Data"}},
        {"skill_id": skill_mastered, "proficiency": 100, "skills": {"id": skill_mastered, "name": "Python", "category": "Core"}},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [
        {"id": skill_gap, "name": "Data Pipelines", "category": "Data"},
        {"id": skill_mastered, "name": "Python", "category": "Core"},
    ]

    candidates = [
        {
            "id": "lesson-mastered",
            "title": "Advanced Python Metaprogramming",
            "associated_skill_id": skill_mastered,
            "difficulty_level": 5,
            "similarity": 0.85,
            "source_trust_score": 0.95,
            "quizzes": [],
        },
        {
            "id": "lesson-gap",
            "title": "Intro to Data Pipelines",
            "associated_skill_id": skill_gap,
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.95,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        results = await rec_service.get_recommendations_for_user(user_id, limit=2)

        # Gap skill must be ranked first
        assert results[0]["associated_skill_id"] == skill_gap
        # Mastered skill is still included (not discarded) with valid positive relevance
        assert results[1]["associated_skill_id"] == skill_mastered
        assert results[1]["relevance_score"] > 0
        assert results[0]["relevance_score"] > results[1]["relevance_score"]


@pytest.mark.asyncio
async def test_semantic_similarity_and_mismatch_filtering(base_user_setup):
    """
    Unrelated content (low similarity or explicit title mismatch) is strongly penalized
    and does not rank above genuine relevant material.
    """
    user_id, career_id, profile_mock, career_mock = base_user_setup
    rec_service = RecommendationService()

    skill_id = "skill-python"
    user_skills_mock = MagicMock()
    user_skills_mock.data = [
        {"skill_id": skill_id, "proficiency": 30, "skills": {"id": skill_id, "name": "Python", "category": "Core"}},
    ]

    all_skills_mock = MagicMock()
    all_skills_mock.data = [{"id": skill_id, "name": "Python", "category": "Core"}]

    candidates = [
        {
            "id": "lesson-relevant",
            "title": "Writing Clean Python Functions",
            "associated_skill_id": skill_id,
            "difficulty_level": 2,
            "similarity": 0.88,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
        {
            "id": "lesson-conflicting-title",
            "title": "Python for Professional Soccer Player",
            "associated_skill_id": skill_id,
            "difficulty_level": 2,
            "similarity": 0.85,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
        {
            "id": "lesson-weak-similarity",
            "title": "Vaguely Related Overview",
            "associated_skill_id": skill_id,
            "difficulty_level": 2,
            "similarity": 0.15,
            "source_trust_score": 0.90,
            "quizzes": [],
        },
    ]

    with patch("app.services.recommendation_service.supabase_client") as mock_sb:
        def table_router(table_name):
            t = MagicMock()
            if table_name == "profiles":
                t.select.return_value.eq.return_value.execute.return_value = profile_mock
            elif table_name == "careers":
                t.select.return_value.eq.return_value.execute.return_value = career_mock
            elif table_name == "user_skills":
                t.select.return_value.eq.return_value.execute.return_value = user_skills_mock
            elif table_name == "career_skills":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skill_dependencies":
                t.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
            elif table_name == "skills":
                t.select.return_value.execute.return_value = all_skills_mock
            return t

        mock_sb.table.side_effect = table_router
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=candidates)
        rec_service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)

        results = await rec_service.get_recommendations_for_user(user_id, limit=3)

        assert results[0]["id"] == "lesson-relevant"
        # The conflicting title and weak similarity lessons must have lower scores
        assert results[0]["relevance_score"] > results[1]["relevance_score"]
        assert results[0]["relevance_score"] > results[2]["relevance_score"]
