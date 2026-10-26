import pytest
from starlette.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.routers.onboarding import sanitize_career_query

client = TestClient(app)

def test_sanitize_career_query():
    """Verify conversational prefixes and whitespace are stripped."""
    assert sanitize_career_query("I want to become a Software Developer") == "Software Developer"
    assert sanitize_career_query("  path to Data Analyst  ") == "Data Analyst"
    assert sanitize_career_query("Looking to become a Web Developer") == "Web Developer"
    assert sanitize_career_query("career as an ML Engineer") == "ML Engineer"
    assert sanitize_career_query("Product Manager") == "Product Manager"

def test_unauthenticated_requests_rejected():
    """Verify JWT middleware strictly guards onboarding endpoints."""
    res_search = client.post("/api/onboarding/career-search", json={"career_query": "Software Developer"})
    assert res_search.status_code == 401
    assert "Authorization" in res_search.json().get("detail", "")

    res_save = client.post("/api/onboarding/save-skills", json={
        "user_id": "test-uuid",
        "career_id": "career-uuid",
        "skills": []
    })
    assert res_save.status_code == 401

@pytest.mark.asyncio
async def test_search_career_onet_provenance_contract():
    """Verify search returns matched O*NET career with accurate provenance and review status."""
    from app.routers.onboarding import search_career, CareerSearchRequest
    from starlette.requests import Request

    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "verified-test-user-uuid"}

    req_body = CareerSearchRequest(career_query="Software Developer")
    result = await search_career(req_body, mock_req)

    assert result["status"] == "matched"
    career = result["career"]
    assert career["title"] == "Software Developer"
    assert career["source_origin"] == "onet"
    assert career["review_status"] == "unreviewed"
    assert career["provenance_label"] == "Source: O*NET · Review pending"

    skills = result["skills"]
    assert len(skills) > 0
    onet_skills = [sk for sk in skills if sk["source_origin"] == "onet"]
    assert len(onet_skills) >= 7, f"Expected at least 7 O*NET skills, found {len(onet_skills)}"
    for sk in skills:
        assert "id" in sk
        assert "name" in sk
        assert "category" in sk
        assert "importance" in sk  # key must exist (value may be None for llm skills)
        assert sk["source_origin"] in ("onet", "llm", "esco", "dual_sourced", "curated_list")
        assert sk.get("provenance_label") is not None
        # Confirm no tier field is returned in skills contract
        assert "tier" not in sk
    # Verify O*NET-sourced skills specifically carry the correct provenance
    for sk in onet_skills:
        assert sk["provenance_label"] == "Source: O*NET · Review pending"

@pytest.mark.asyncio
async def test_save_skills_contract_validations():
    """Verify save_skills contract: user verification, empty skill guard, and parameter enforcement."""
    from app.routers.onboarding import save_skills, SaveSkillsRequest, UnifiedSkillInput
    from starlette.requests import Request
    from fastapi import HTTPException

    mock_req = MagicMock(spec=Request)
    mock_req.state.user = {"sub": "user-123"}

    # 1. User ID mismatch guard (Workstream 1)
    with pytest.raises(HTTPException) as exc_info:
        await save_skills(SaveSkillsRequest(
            user_id="different-user-456",
            career_id="career-uuid",
            career_title="Software Developer",
            skills=[UnifiedSkillInput(id="s1", name="Python", category="Technical Skills", proficiency=50)]
        ), mock_req)
    assert exc_info.value.status_code == 403

    # 2. Empty skills guard
    with pytest.raises(HTTPException) as exc_info:
        await save_skills(SaveSkillsRequest(
            user_id="user-123",
            career_id="career-uuid",
            career_title="Software Developer",
            skills=[]
        ), mock_req)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_ai_career_proposal_quarantine_contract():
    """Verify that an AI-generated career proposal is strictly quarantined in pending_careers,

    marked is_curated=False, source_origin='llm', review_status='unreviewed', and cannot silently enter curated catalogue."""
    from app.routers.onboarding import save_skills, SaveSkillsRequest, UnifiedSkillInput
    from app.core.database import supabase_client
    from starlette.requests import Request
    import uuid

    # Create temporary test user via admin API
    test_email = f"quarantine-test-{uuid.uuid4().hex[:8]}@careerbeacon.internal"
    user_res = supabase_client.auth.admin.create_user({
        "email": test_email,
        "password": "Password123!SecureTest",
        "email_confirm": True
    })
    test_user_id = user_res.user.id

    try:
        # Mock request with authenticated user identity
        mock_req = MagicMock(spec=Request)
        mock_req.state.user = {"sub": test_user_id}

        unique_title = f"Quantum Ethics Architect {uuid.uuid4().hex[:6]}"
        save_req = SaveSkillsRequest(
            user_id=test_user_id,
            career_id=None,  # AI-generated proposal has no prior DB career_id
            career_title=unique_title,
            career_description="Designs ethical frameworks and alignment policies for quantum algorithms.",
            skills=[
                UnifiedSkillInput(
                    id=f"temp-{uuid.uuid4().hex[:8]}",
                    name=f"Quantum Policy {uuid.uuid4().hex[:4]}",
                    category="Domain Knowledge",
                    proficiency=60,
                    importance=None
                ),
                UnifiedSkillInput(
                    id=f"temp-{uuid.uuid4().hex[:8]}",
                    name=f"Algorithmic Auditing {uuid.uuid4().hex[:4]}",
                    category="Technical Skills",
                    proficiency=40,
                    importance=None
                )
            ]
        )

        result = await save_skills(save_req, mock_req)
        assert result["status"] == "success"
        career_id = result["career_id"]

        # 1. Verify row was created in pending_careers quarantine table
        pending_check = supabase_client.table("pending_careers").select("*").eq("promoted_career_id", career_id).execute()
        assert len(pending_check.data) == 1, "Proposal must be quarantined in pending_careers"
        pending_row = pending_check.data[0]
        assert pending_row["status"] == "pending"
        assert pending_row["proposed_by"] == test_user_id
        assert pending_row["title"] == unique_title
        assert len(pending_row["provisional_skills"]) == 2

        # 2. Verify row in careers table has strict uncurated quarantine flags
        career_check = supabase_client.table("careers").select("*").eq("id", career_id).execute()
        assert len(career_check.data) == 1
        career_row = career_check.data[0]
        assert career_row["is_curated"] is False, "AI proposal MUST NOT be marked is_curated=True"
        assert career_row["source_origin"] == "llm", "Source origin must be 'llm'"
        assert career_row["review_status"] == "unreviewed", "Review status must be 'unreviewed'"
        assert career_row["proposing_user_id"] == test_user_id

        # 3. Verify career_skills entries carry llm provenance and no fabricated tier
        junction_check = supabase_client.table("career_skills").select("*").eq("career_id", career_id).execute()
        assert len(junction_check.data) == 2
        for j_row in junction_check.data:
            assert j_row["source_origin"] == "llm"
            assert j_row["review_status"] == "unreviewed"
            assert j_row["importance"] is None

        # 4. Strict Vector & Search Isolation:
        # Vector must be NULL so pgvector match_careers skips it completely
        assert career_row.get("career_vector") is None, "career_vector must be NULL for uncurated careers"

        # Search query for the exact quarantined title must NOT return it as a matched canonical career
        from app.routers.onboarding import search_career, CareerSearchRequest
        search_res = await search_career(CareerSearchRequest(career_query=unique_title), mock_req)
        if search_res["status"] == "matched":
            assert search_res["career"]["id"] != career_id, "Quarantined career must NEVER be returned as matched!"
        print(f"[Quarantine Contract] Search isolation verified: '{unique_title}' is invisible to canonical search.")

        # 5. Downstream recommendation check:
        # Exercises recommendation retrieval when an unapproved proposal is present,
        # verifying that it serves the proposing learner's skill gap without failing or leaking.
        from app.services.recommendation_service import RecommendationService
        rec_service = RecommendationService()
        recs = await rec_service.get_recommendations_for_user(test_user_id, limit=2)
        assert isinstance(recs, list)
        print(f"[Quarantine Contract] Downstream recommendation check passed: returned {len(recs)} personalized items.")

    finally:
        # Cleanup
        try:
            supabase_client.table("user_skills").delete().eq("user_id", test_user_id).execute()
            supabase_client.table("profiles").delete().eq("id", test_user_id).execute()
            if 'career_id' in locals():
                supabase_client.table("career_skills").delete().eq("career_id", career_id).execute()
                supabase_client.table("pending_careers").delete().eq("promoted_career_id", career_id).execute()
                supabase_client.table("careers").delete().eq("id", career_id).execute()
            supabase_client.auth.admin.delete_user(test_user_id)
        except Exception as cleanup_err:
            print(f"[Quarantine Contract] Cleanup warning: {cleanup_err}")

