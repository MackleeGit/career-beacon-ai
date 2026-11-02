from fastapi import APIRouter, HTTPException
from app.models.schemas import EmbeddingRequest, EmbeddingResponse, GenerationRequest, GenerationResponse
from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client

router = APIRouter(prefix="/api/test", tags=["Verification / Verification Endpoints"])
ai_service = AIService()
embedding_service = EmbeddingService()

@router.post("/minilm-embedding", response_model=EmbeddingResponse)
async def test_minilm_embedding(request: EmbeddingRequest):
    try:
        embedding = await embedding_service.get_embedding(request.text)
        return EmbeddingResponse(embedding=embedding, dimensions=len(embedding))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")

@router.post("/ai-generate", response_model=GenerationResponse)
async def test_ai_generate(request: GenerationRequest):
    try:
        data = await ai_service.generate_json(request.prompt, request.system_instruction)
        return GenerationResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate JSON content: {str(e)}")

@router.get("/supabase")
async def test_supabase_connection():
    try:
        # Fetch pre-seeded careers to verify read capabilities
        response = supabase_client.table("careers").select("*").execute()
        return {
            "status": "connected",
            "table": "careers",
            "record_count": len(response.data),
            "records": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase Database Connection Failed: {str(e)}")


@router.get("/db-audit")
async def audit_database():
    audit = {}
    try:
        # 1. Profiles
        p_res = supabase_client.table("profiles").select("id, role, username, email, full_name, created_at").execute()
        profiles = p_res.data or []
        roles = {}
        missing_username = 0
        missing_email = 0
        for p in profiles:
            r = p.get("role") or "unassigned"
            roles[r] = roles.get(r, 0) + 1
            if not p.get("username"):
                missing_username += 1
            if not p.get("email"):
                missing_email += 1

        audit["profiles"] = {
            "total": len(profiles),
            "by_role": roles,
            "missing_username": missing_username,
            "missing_email": missing_email,
            "sample_users": [{"id": p["id"][:8], "role": p.get("role"), "username": p.get("username"), "email": p.get("email")} for p in profiles[:10]],
        }

        # 2. Careers
        c_res = supabase_client.table("careers").select("id, title, source_origin, review_status").execute()
        careers = c_res.data or []
        origins = {}
        review_statuses = {}
        title_counts = {}
        plural_candidates = []
        for c in careers:
            t = (c.get("title") or "").strip()
            title_counts[t.lower()] = title_counts.get(t.lower(), 0) + 1
            o = c.get("source_origin") or "unknown"
            origins[o] = origins.get(o, 0) + 1
            st = c.get("review_status") or "unreviewed"
            review_statuses[st] = review_statuses.get(st, 0) + 1
            if t.endswith("s") and not t.endswith("ss") and not t.endswith("ics") and not t.endswith("us"):
                plural_candidates.append(t)

        duplicates = {k: v for k, v in title_counts.items() if v > 1}
        audit["careers"] = {
            "total": len(careers),
            "by_source_origin": origins,
            "by_review_status": review_statuses,
            "duplicate_titles_count": len(duplicates),
            "duplicate_titles": list(duplicates.keys())[:10],
            "plural_flagged_count": len(plural_candidates),
            "plural_samples": plural_candidates[:5],
        }

        # 3. Skills & Career Skills
        sk_res = supabase_client.table("skills").select("id, name, category").execute()
        skills = sk_res.data or []
        cs_res = supabase_client.table("career_skills").select("career_id, skill_id, importance").execute()
        career_skills = cs_res.data or []
        cs_importance = {}
        for cs in career_skills:
            imp = cs.get("importance") or "unassigned"
            cs_importance[imp] = cs_importance.get(imp, 0) + 1

        audit["skills_taxonomy"] = {
            "total_skills": len(skills),
            "total_career_skills_relations": len(career_skills),
            "importance_breakdown": cs_importance,
        }

        # 4. User Skills
        us_res = supabase_client.table("user_skills").select("user_id, skill_id, proficiency, evidence_source").execute()
        user_skills = us_res.data or []
        evidence = {}
        users_with_skills = set()
        for us in user_skills:
            users_with_skills.add(us.get("user_id"))
            ev = us.get("evidence_source") or "none"
            evidence[ev] = evidence.get(ev, 0) + 1

        audit["user_skills"] = {
            "total_records": len(user_skills),
            "unique_learners": len(users_with_skills),
            "evidence_sources": evidence,
        }

        # 5. Mentors (Supabase Table + JSON Store)
        m_db_res = supabase_client.table("mentors").select("id, full_name, primary_domain, is_verified, weekly_hours, max_mentees").execute()
        db_mentors = m_db_res.data or []

        from app.services.mentorship_service import mentorship_service
        store = mentorship_service._ensure_store()
        store_mentors = store.get("mentors", [])
        store_sessions = store.get("sessions", [])
        store_conns = store.get("connections", [])
        store_questions = store.get("questions", [])

        audit["mentorship_ecosystem"] = {
            "supabase_mentors_table_count": len(db_mentors),
            "ecosystem_store_mentors_count": len(store_mentors),
            "seeded_mentors_count": sum(1 for m in store_mentors if m.get("is_seeded")),
            "organic_mentors_count": sum(1 for m in store_mentors if not m.get("is_seeded")),
            "total_sessions": len(store_sessions),
            "session_statuses": {st: sum(1 for s in store_sessions if s.get("status") == st) for st in set(s.get("status") for s in store_sessions)},
            "total_connections": len(store_conns),
            "connection_statuses": {st: sum(1 for c in store_conns if c.get("status") == st) for st in set(c.get("status") for c in store_conns)},
            "total_questions": len(store_questions),
        }

        audit["is_clean"] = (
            len(duplicates) == 0
            and missing_email == 0
            and len(careers) >= 700
            and len(skills) >= 100
        )

        return {"status": "success", "audit": audit}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database audit failed: {e}")
