from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

embedding_service = EmbeddingService()
ai_service = AIService()

class CareerSearchRequest(BaseModel):
    career_query: str

class SkillProficiency(BaseModel):
    # For matched careers: skill_id is the real UUID from DB
    # For pending (AI-generated) careers: skill_id is a temporary client-side key
    skill_id: str
    proficiency: int  # 20, 50, 80

class PendingSkill(BaseModel):
    """Skill data returned from AI that hasn't been saved yet."""
    name: str
    category: str

class SaveSkillsRequest(BaseModel):
    user_id: str
    # For DB-matched careers:
    career_id: str | None = None
    # For AI-generated (pending) careers that haven't been saved yet:
    pending_career_title: str | None = None
    pending_career_description: str | None = None
    pending_skills: List[PendingSkill] | None = None  # full skill objects for pending
    # For matched careers, we use saved skill IDs:
    skills: List[SkillProficiency] | None = None

@router.post("/career-search")
async def search_career(request: CareerSearchRequest):
    query = request.career_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Career query is empty")

    # 1. Embed the user's query
    query_vector = await embedding_service.get_embedding(query)

    # 2. Search Supabase for existing careers using semantic vector search
    SIMILARITY_THRESHOLD = 0.88
    try:
        response = supabase_client.rpc(
            "match_careers",
            {"query_embedding": query_vector, "match_threshold": SIMILARITY_THRESHOLD, "match_count": 1}
        ).execute()

        if response.data and len(response.data) > 0:
            matched_career = response.data[0]
            # Guard: Supabase RPC may return the closest match even below threshold.
            # Enforce the threshold ourselves using the similarity score in the response.
            similarity = matched_career.get("similarity", 0)
            print(f"[career-search] Best match: '{matched_career.get('title')}' | similarity={similarity:.4f} | threshold={SIMILARITY_THRESHOLD}")

            if similarity < SIMILARITY_THRESHOLD:
                print(f"[career-search] Match rejected (score too low). Falling back to AI.")
            else:
                # Fetch the associated skills
                skills_res = supabase_client.table("career_skills").select("skills(*)").eq("career_id", matched_career["id"]).execute()
                skills = [row["skills"] for row in skills_res.data if row.get("skills")]
                return {
                    "status": "matched",
                    "career": matched_career,
                    "skills": skills
                }
    except Exception as e:
        print("RPC error:", e)
        # Continue to AI fallback if RPC fails or no match found

    # 3. AI Fallback: Generate standardized career and 8 skills
    system_prompt = """You are an expert career and skills analyst. The user will provide a raw, potentially messy career target string.
    You must:
    1. Standardize it into a recognized professional job title.
    2. Generate an array of 8 exact, highly relevant technical skills required for this job. Keep the skills brief (e.g. "Python", "Docker", "UI/UX Design").
    Output in strictly valid JSON format matching this structure exactly:
    {
        "title": "Standardized Career Title",
        "description": "A short 1-sentence description of what this role does.",
        "skills": [
            {"name": "Skill 1", "category": "Category A"},
            {"name": "Skill 2", "category": "Category B"}
        ]
    }
    """
    try:
        ai_data = await ai_service.generate_json(query, system_instruction=system_prompt)
    except Exception as ai_err:
        print(f"AI provider error: {ai_err}")
        raise HTTPException(
            status_code=503,
            detail=f"AI career generation is currently unavailable. Please try again later."
        )

    # ── Return ephemeral data — nothing is saved until the user completes the skill graph ──
    # We attach temporary client-side IDs so the frontend can reference each skill.
    import uuid
    pending_skills = [
        {"id": str(uuid.uuid4()), "name": sk["name"], "category": sk["category"]}
        for sk in ai_data["skills"]
    ]
    return {
        "status": "generated",
        "career": {
            "id": None,  # No DB ID yet — will be assigned on save-skills
            "title": ai_data["title"],
            "description": ai_data["description"],
            "_pending": True,  # Flag so frontend knows this isn't committed
        },
        "skills": pending_skills
    }

@router.post("/save-skills")
async def save_skills(request: SaveSkillsRequest):
    """
    Commits a completed onboarding session to the database.
    Handles two cases:
    - Matched career: career_id is known, skills have real UUIDs.
    - Pending career: career was AI-generated, we save it here for the first time.
    """
    try:
        career_id = request.career_id

        # ── Case A: AI-generated career that hasn't been persisted yet ──
        if not career_id and request.pending_career_title:
            career_vector = await embedding_service.get_embedding(
                f"{request.pending_career_title}: {request.pending_career_description or ''}"
            )
            career_res = supabase_client.table("careers").insert({
                "title": request.pending_career_title,
                "description": request.pending_career_description,
                "career_vector": career_vector,
            }).execute()
            career_id = career_res.data[0]["id"]

            # Upsert skills and link them to the new career
            skill_proficiency_map = {}
            if request.pending_skills and request.skills:
                # Build a name→proficiency map from the client-side proficiency list
                # The frontend sends pending_skills with names, and skills with temp IDs + proficiency
                temp_id_to_proficiency = {sk.skill_id: sk.proficiency for sk in request.skills}

            skill_ids_with_proficiency = []
            for i, sk in enumerate(request.pending_skills or []):
                exist_sk = supabase_client.table("skills").select("*").eq("name", sk.name).execute()
                if exist_sk.data:
                    real_sk = exist_sk.data[0]
                else:
                    new_sk = supabase_client.table("skills").insert({
                        "name": sk.name,
                        "category": sk.category,
                    }).execute()
                    real_sk = new_sk.data[0]

                supabase_client.table("career_skills").insert({
                    "career_id": career_id,
                    "skill_id": real_sk["id"],
                    "rank": i + 1,
                }).execute()

                # Find the proficiency for this skill using position index
                proficiency = 20  # default novice
                if request.skills and i < len(request.skills):
                    proficiency = request.skills[i].proficiency

                skill_ids_with_proficiency.append((real_sk["id"], proficiency))

            # Update profile and upsert user_skills
            supabase_client.table("profiles").update({"target_career_id": career_id}).eq("id", request.user_id).execute()
            supabase_client.table("user_skills").upsert([
                {"user_id": request.user_id, "skill_id": sid, "proficiency": prof}
                for sid, prof in skill_ids_with_proficiency
            ]).execute()

            return {"status": "success", "message": "Career and skills saved successfully"}

        # ── Case B: Matched career — skills already have real DB UUIDs ──
        supabase_client.table("profiles").update({"target_career_id": career_id}).eq("id", request.user_id).execute()

        inserts = [
            {"user_id": request.user_id, "skill_id": sk.skill_id, "proficiency": sk.proficiency}
            for sk in (request.skills or [])
        ]
        if inserts:
            supabase_client.table("user_skills").upsert(inserts).execute()

        return {"status": "success", "message": "Skills saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save skills: {str(e)}")


@router.get("/status/{user_id}")
async def get_onboarding_status(user_id: str):
    """
    Returns whether a user has completed onboarding (i.e. has a target_career_id set
    and at least one skill saved in user_skills).
    """
    try:
        profile_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).single().execute()
        profile = profile_res.data

        if not profile or not profile.get("target_career_id"):
            return {"onboarding_complete": False, "career": None, "skills": []}

        career_id = profile["target_career_id"]

        # Fetch career info
        career_res = supabase_client.table("careers").select("id, title, description").eq("id", career_id).single().execute()
        career = career_res.data

        # Fetch saved user skills with full skill details
        skills_res = supabase_client.table("user_skills").select("proficiency, skills(id, name, category)").eq("user_id", user_id).execute()
        skills = [
            {**row["skills"], "proficiency": row["proficiency"]}
            for row in skills_res.data if row.get("skills")
        ]

        return {
            "onboarding_complete": len(skills) > 0,
            "career": career,
            "skills": skills
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch onboarding status: {str(e)}")

