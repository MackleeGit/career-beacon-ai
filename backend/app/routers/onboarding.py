from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

embedding_service = EmbeddingService()
gemini_service = GeminiService()

class CareerSearchRequest(BaseModel):
    career_query: str

class SkillProficiency(BaseModel):
    skill_id: str
    proficiency: int  # 20, 50, 80

class SaveSkillsRequest(BaseModel):
    user_id: str
    career_id: str
    skills: List[SkillProficiency]

@router.post("/career-search")
async def search_career(request: CareerSearchRequest):
    query = request.career_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Career query is empty")

    # 1. Embed the user's query
    query_vector = await embedding_service.get_embedding(query)

    # 2. Search Supabase for existing careers with similarity > 0.85
    try:
        response = supabase_client.rpc(
            "match_careers",
            {"query_embedding": query_vector, "match_threshold": 0.85, "match_count": 1}
        ).execute()

        if response.data and len(response.data) > 0:
            matched_career = response.data[0]
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
        ai_data = await gemini_service.generate_json(query, system_instruction=system_prompt)
        
        # 4. Save to Database
        # 4a. Embed the new career title
        career_vector = await embedding_service.get_embedding(ai_data["title"])
        
        # Insert Career
        career_res = supabase_client.table("careers").insert({
            "title": ai_data["title"],
            "description": ai_data["description"],
            "career_vector": career_vector
        }).execute()
        
        new_career = career_res.data[0]
        career_id = new_career["id"]
        
        # Insert Skills (Upsert to avoid duplicates, although we need to handle this carefully)
        inserted_skills = []
        for sk in ai_data["skills"]:
            # Try to find existing skill
            exist_sk = supabase_client.table("skills").select("*").eq("name", sk["name"]).execute()
            if exist_sk.data:
                sk_id = exist_sk.data[0]["id"]
                inserted_skills.append(exist_sk.data[0])
            else:
                new_sk = supabase_client.table("skills").insert({
                    "name": sk["name"],
                    "category": sk["category"]
                }).execute()
                sk_id = new_sk.data[0]["id"]
                inserted_skills.append(new_sk.data[0])
            
            # Link to career
            supabase_client.table("career_skills").insert({
                "career_id": career_id,
                "skill_id": sk_id,
                "rank": 1
            }).execute()

        return {
            "status": "generated",
            "career": new_career,
            "skills": inserted_skills
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate career path: {str(e)}")

@router.post("/save-skills")
async def save_skills(request: SaveSkillsRequest):
    try:
        # Update user's profile with their target career
        supabase_client.table("profiles").update({"target_career_id": request.career_id}).eq("id", request.user_id).execute()

        # Upsert user_skills
        inserts = []
        for sk in request.skills:
            inserts.append({
                "user_id": request.user_id,
                "skill_id": sk.skill_id,
                "proficiency": sk.proficiency
            })
        
        # Using upsert
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

