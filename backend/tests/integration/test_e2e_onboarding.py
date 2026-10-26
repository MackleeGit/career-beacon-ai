import os
import sys
import uuid
import pytest
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / 'backend' / '.env'
load_dotenv(env_path)

sys.path.append(str(Path(__file__).resolve().parent.parent / 'backend'))
from app.core.database import supabase_client
from app.routers.onboarding import search_career, save_skills, get_onboarding_status, CareerSearchRequest, SaveSkillsRequest, UnifiedSkillInput
from app.services.recommendation_service import RecommendationService
from starlette.requests import Request
from unittest.mock import MagicMock

@pytest.mark.asyncio
@pytest.mark.live_supabase
async def test_end_to_end_onboarding_and_regression():
    # 1. Setup a real auth test user via Supabase admin API
    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"e2e-test-{unique_suffix}@careerbeacon.internal"
    
    auth_user = supabase_client.auth.admin.create_user({
        "email": test_email,
        "password": "TemporaryTestPassword123!",
        "email_confirm": True,
    })
    test_user_id = auth_user.user.id
    print(f"\n[E2E] Provisioned auth test user: {test_user_id} ({test_email})")

    try:
        mock_req = MagicMock(spec=Request)
        mock_req.state.user = {"sub": test_user_id}

        # Step 1: Initial status check (should be onboarding_complete=False)
        init_status = await get_onboarding_status(test_user_id, mock_req)
        assert init_status["onboarding_complete"] is False
        assert init_status["career"] is None
        assert len(init_status["skills"]) == 0
        print("[E2E] Initial onboarding state verified: onboarding_complete=False")

        # Step 2: Search for career (testing NLP query hygiene & O*NET match)
        search_res = await search_career(CareerSearchRequest(career_query="I want to become a Software Developer"), mock_req)
        assert search_res["status"] == "matched"
        matched_career = search_res["career"]
        matched_skills = search_res["skills"]
        assert matched_career["title"] == "Software Developer"
        assert matched_career["provenance_label"] == "Source: O*NET · Review pending"
        assert len(matched_skills) >= 7
        print(f"[E2E] Matched career '{matched_career['title']}' with {len(matched_skills)} source-backed skills")

        # Step 3: Customize skills (set behavioral proficiencies + add 1 custom stack tool)
        skills_to_save = [
            UnifiedSkillInput(
                id=s["id"],
                name=s["name"],
                category=s["category"],
                proficiency=50 if i % 2 == 0 else 20, # Alternate Novice and Intermediate
                importance=s.get("importance")
            )
            for i, s in enumerate(matched_skills)
        ]
        # Add custom stack tool (e.g. Supabase Backend Integration)
        skills_to_save.append(UnifiedSkillInput(
            id=None,
            name=f"E2E Test Tool {unique_suffix}",
            category="Tools & Systems",
            proficiency=80,
            importance=None
        ))

        # Step 4: Commit skills via save_skills
        save_payload = SaveSkillsRequest(
            user_id=test_user_id,
            career_id=matched_career["id"],
            career_title=matched_career["title"],
            career_description=matched_career.get("description", ""),
            is_custom=False,
            skills=skills_to_save
        )
        save_res = await save_skills(save_payload, mock_req)
        assert save_res["status"] == "success"
        print(f"[E2E] Successfully saved {save_res['skills_count']} skills to database")

        # Step 5: Simulate page reload / revisit by calling get_onboarding_status again
        reloaded_status = await get_onboarding_status(test_user_id, mock_req)
        assert reloaded_status["onboarding_complete"] is True
        assert reloaded_status["career"]["id"] == matched_career["id"]
        assert reloaded_status["career"]["title"] == "Software Developer"
        assert len(reloaded_status["skills"]) == len(skills_to_save)
        
        # Check custom skill persistence and proficiencies
        persisted_skill_names = {s["name"]: s["proficiency"] for s in reloaded_status["skills"]}
        assert f"E2E Test Tool {unique_suffix}" in persisted_skill_names
        assert persisted_skill_names[f"E2E Test Tool {unique_suffix}"] == 80
        print("[E2E] Page reload simulation verified: career and skill graph persisted accurately")

        # Step 6: Verify evidence_source contract in database
        db_user_skills = supabase_client.table("user_skills").select("skill_id, proficiency, evidence_source").eq("user_id", test_user_id).execute().data
        assert len(db_user_skills) == len(skills_to_save)
        for us in db_user_skills:
            assert us["evidence_source"] == "self_reported"
        print("[E2E] Database evidence_source contract verified: all rows self_reported")

        # Step 7: Regression check: Recommendation retrieval based on newly calibrated skill gaps
        rec_service = RecommendationService()
        recs = await rec_service.get_recommendations_for_user(test_user_id, limit=3)
        assert isinstance(recs, list)
        print(f"[E2E] Recommendation engine regression check passed: returned {len(recs)} personalized items")

        print("\n=== E2E ONBOARDING & REGRESSION VERDICT: 100% PASSED ===")

    finally:
        # Cleanup: delete user_skills, profile, and auth user
        try:
            supabase_client.table("user_skills").delete().eq("user_id", test_user_id).execute()
            supabase_client.table("profiles").delete().eq("id", test_user_id).execute()
            supabase_client.auth.admin.delete_user(test_user_id)
            print(f"[E2E] Cleaned up temporary auth user: {test_user_id}")
        except Exception as cleanup_err:
            print(f"[E2E] Cleanup warning: {cleanup_err}")
