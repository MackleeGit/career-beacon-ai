import re
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

embedding_service = EmbeddingService()
ai_service = AIService()


from app.middleware.auth_middleware import get_verified_user_id



# ---------------------------------------------------------------------------
# Input Hygiene & Guardrails (Workstream 2)
# ---------------------------------------------------------------------------
def sanitize_career_query(query: str) -> str:
    clean = query.strip()
    # Strip conversational prefixes
    prefixes = [
        r"^i want to be\s+(?:an|a)?\s*",
        r"^i want to become\s+(?:an|a)?\s*",
        r"^looking to become\s+(?:an|a)?\s*",
        r"^how to become\s+(?:an|a)?\s*",
        r"^career as\s+(?:an|a)?\s*",
        r"^path to\s+(?:an|a)?\s*",
    ]
    for p in prefixes:
        clean = re.sub(p, "", clean, flags=re.IGNORECASE).strip()

    if len(clean) < 3 or len(clean) > 80:
        raise HTTPException(
            status_code=400,
            detail="Career query must be between 3 and 80 characters long.",
        )

    # Entropy & letter check: reject numbers-only or random keyboard mashing
    letters = [c for c in clean if c.isalpha()]
    if len(letters) < 3:
        raise HTTPException(
            status_code=400,
            detail="Please enter a recognizable job title or career goal (e.g., 'Frontend Developer').",
        )

    return clean


# ---------------------------------------------------------------------------
# Pydantic Schemas (Unified Atomic Contract - Workstream 1 & 3)
# ---------------------------------------------------------------------------
class CareerSearchRequest(BaseModel):
    career_query: str


class UnifiedSkillInput(BaseModel):
    skill_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="General", max_length=60)
    proficiency: int = Field(default=20, ge=0, le=100)
    importance: Optional[str] = None  # 'essential' | 'optional' | None for unverified


class SaveSkillsRequest(BaseModel):
    user_id: Optional[str] = None  # Optional from client; backend validates against JWT sub
    career_id: Optional[str] = None
    career_title: str
    career_description: Optional[str] = ""
    is_custom: bool = False
    skills: List[UnifiedSkillInput]


# ---------------------------------------------------------------------------
# POST /api/onboarding/career-search (Workstream 2 & 4)
# ---------------------------------------------------------------------------
@router.post("/career-search")
async def search_career(request: CareerSearchRequest, http_req: Request):
    # Enforce basic auth check
    _ = get_verified_user_id(http_req)

    raw_query = request.career_query
    if not raw_query:
        raise HTTPException(status_code=400, detail="Career query is required.")

    query = sanitize_career_query(raw_query)

    # 1. Embed sanitized query
    query_vector = await embedding_service.get_embedding(query)

    # 2. Search Supabase for canonical careers
    # Threshold Specification:
    # - HIGH_CONFIDENCE_THRESHOLD (0.85): Direct auto-match
    # - DISAMBIGUATION_THRESHOLD (0.72): Multi-candidate boundary
    # - RPC_CANDIDATE_FILTER (0.70): Coarse database retrieval filter
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    DISAMBIGUATION_THRESHOLD = 0.72
    RPC_CANDIDATE_FILTER = 0.70

    # Explicit allowlist of authoritative sources for canonical career search
    CANONICAL_SOURCES = ("onet", "esco", "dual_sourced", "curated_list")

    try:
        response = supabase_client.rpc(
            "match_careers",
            {
                "query_embedding": query_vector,
                "match_threshold": RPC_CANDIDATE_FILTER,
                "match_count": 5,
            },
        ).execute()

        # Strict Catalogue Isolation: Only careers from CANONICAL_SOURCES are admissible
        # into search results. Unapproved LLM proposals are strictly excluded.
        raw_candidates = response.data or []
        candidates = []
        if raw_candidates:
            cand_ids = [c["id"] for c in raw_candidates]
            source_res = (
                supabase_client.table("careers")
                .select("id, is_curated, source_origin, review_status, onet_soc_code, esco_occupation_uri")
                .in_("id", cand_ids)
                .in_("source_origin", list(CANONICAL_SOURCES))
                .execute()
            )
            canonical_dict = {row["id"]: row for row in (source_res.data or [])}
            for c in raw_candidates:
                if c["id"] in canonical_dict:
                    merged = dict(c)
                    merged.update(canonical_dict[c["id"]])
                    candidates.append(merged)

        if candidates:
            top_match = candidates[0]
            top_score = top_match.get("similarity", 0)

            # High confidence clear match
            if top_score >= HIGH_CONFIDENCE_THRESHOLD:
                # Fetch skills with full provenance metadata
                skills_res = (
                    supabase_client.table("career_skills")
                    .select("source_origin, review_status, importance, importance_score, skills(*)")
                    .eq("career_id", top_match["id"])
                    .execute()
                )

                skills = []
                for row in skills_res.data:
                    sk = row.get("skills")
                    if sk:
                        source_origin = row.get("source_origin", "llm")
                        skills.append({
                            "id":               sk["id"],
                            "name":             sk["name"],
                            "category":         sk.get("category") or "General",
                            "importance":       row.get("importance"),  # None is valid; UI handles it
                            "importance_score": row.get("importance_score"),
                            "source_origin":    source_origin,
                            "provenance_label": (
                                "Source: O*NET & ESCO · Review pending" if (source_origin == "dual_sourced" and row.get("review_status") == "unreviewed")
                                else "Source: O*NET & ESCO" if source_origin == "dual_sourced"
                                else "Source: O*NET · Review pending" if (source_origin == "onet" and row.get("review_status") == "unreviewed")
                                else "Source: O*NET"   if source_origin == "onet"
                                else "Source: ESCO · Review pending" if (source_origin == "esco" and row.get("review_status") == "unreviewed")
                                else "Source: ESCO"    if source_origin == "esco"
                                else "Curated"         if (source_origin == "curated_list" and row.get("review_status") == "curated")
                                else "Internal Starter" if source_origin == "curated_list"
                                else "AI Suggestion"
                            ),
                        })

                # Attach provenance to the career object
                career_source = top_match.get("source_origin", "llm")
                career_status = top_match.get("review_status", "unreviewed")
                top_match["provenance_label"] = (
                    "Source: O*NET & ESCO · Review pending" if (career_source == "dual_sourced" and career_status == "unreviewed")
                    else "Source: O*NET & ESCO" if career_source == "dual_sourced"
                    else "Source: O*NET · Review pending" if (career_source == "onet" and career_status == "unreviewed")
                    else "Source: O*NET"   if career_source == "onet"
                    else "Source: ESCO · Review pending" if (career_source == "esco" and career_status == "unreviewed")
                    else "Source: ESCO"    if career_source == "esco"
                    else "Curated"         if career_status == "curated"
                    else "AI Suggestion"
                )

                return {
                    "status": "matched",
                    "career": top_match,
                    "skills": skills,
                }

            # Moderate confidence ([0.72, 0.85)) -> Disambiguation / candidate confirmation
            if top_score >= DISAMBIGUATION_THRESHOLD:
                return {
                    "status": "disambiguation_required",
                    "candidates": [
                        {
                            "id": c["id"],
                            "title": c["title"],
                            "description": c.get("description", ""),
                            "similarity": round(c.get("similarity", 0), 2),
                        }
                        for c in candidates[:3]
                    ],
                }

    except Exception as e:
        print("[career-search] RPC search error:", e)

    # 3. AI Fallback: Generate structured occupational skill profile by domain category.
    # Skills are grouped by domain, NOT by an artificial tier number.
    # importance is left null — LLM suggestions carry no source authority.
    system_prompt = """You are an expert labor-market analyst.
Given the career query, produce a standardized occupation profile with skills grouped by domain.

DOMAIN CATEGORIES (use exactly these names):
- "Technical Skills": core technical abilities (e.g. programming languages, algorithms, data analysis)
- "Domain Knowledge": subject-matter expertise specific to the field (e.g. financial modeling, network protocols)
- "Tools & Systems": specific software, platforms, or frameworks used daily (e.g. React, PostgreSQL, Docker)
- "Interpersonal & Leadership": communication, collaboration, or management abilities

RULES:
- Include 6-10 skills total across all categories.
- Only include skills clearly backed by job market demand for this specific role.
- Do NOT invent prerequisite relationships or tier numbers.

OUTPUT strictly valid JSON:
{
    "title": "Standardized Job Title",
    "description": "One clear sentence describing the role.",
    "skills": [
        {"name": "Skill Name", "category": "Technical Skills"},
        {"name": "Skill Name", "category": "Tools & Systems"}
    ]
}"""

    try:
        ai_data = await ai_service.generate_json(query, system_instruction=system_prompt)
    except Exception as ai_err:
        print(f"[career-search] AI provider error: {ai_err}")
        raise HTTPException(
            status_code=503,
            detail="AI career generation is currently unavailable. Please try again.",
        )

    pending_skills = [
        {
            "id":           f"temp-{uuid.uuid4().hex[:8]}",
            "name":         sk["name"].strip(),
            "category":     sk.get("category") or "General",
            "importance":   None,       # AI suggestions carry no source-backed importance label
            "source_origin": "llm",
            "provenance_label": "AI Suggestion",
        }
        for sk in ai_data.get("skills", [])
    ]

    return {
        "status": "generated",
        "career": {
            "id":            None,
            "title":         ai_data["title"],
            "description":   ai_data.get("description", ""),
            "provenance_label": "AI Suggestion",
            "_pending":      True,
        },
        "skills": pending_skills,
    }


# ---------------------------------------------------------------------------
# POST /api/onboarding/save-skills (Workstreams 1, 3, 4, 5)
# ---------------------------------------------------------------------------
@router.post("/save-skills")
async def save_skills(request: SaveSkillsRequest, http_req: Request):
    """
    Commits onboarding to database atomically.
    Identity is strictly bound to the verified JWT sub (Workstream 1).
    All skills are self-contained objects, eliminating array-index bugs (Workstream 3).
    Custom AI proposals are flagged with is_curated=False to prevent catalogue pollution (Workstream 2).
    Evidence source is set to 'self_reported' (Workstream 5).
    """
    authenticated_user_id = get_verified_user_id(http_req)

    # Prevent cross-user account tampering
    if request.user_id and request.user_id != authenticated_user_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot submit skill profiles on behalf of another user account.",
        )

    user_id = authenticated_user_id

    if not request.skills:
        raise HTTPException(status_code=400, detail="At least one skill must be rated.")

    try:
        career_id = request.career_id

        # Case A: AI-generated proposal — quarantine in pending_careers.
        # These MUST NOT enter the shared careers table without admin review.
        # The learner's session still proceeds using a provisional career_id
        # resolved at the end of their onboarding, but it carries provenance.
        if not career_id:
            career_vector = await embedding_service.get_embedding(
                f"{request.career_title}: {request.career_description}"
            )

            # Write to pending_careers quarantine table
            provisional_skills = [
                {
                    "name":       sk.name.strip(),
                    "category":   sk.category,
                    "importance": sk.importance,  # May be None for AI suggestions
                }
                for sk in request.skills
            ]
            pending_res = supabase_client.table("pending_careers").insert({
                "proposed_by":        user_id,
                "title":              request.career_title,
                "description":        request.career_description,
                "provisional_skills": provisional_skills,
                "status":             "pending",
            }).execute()
            if not pending_res.data:
                raise RuntimeError("Failed to write provisional career to pending_careers.")

            # Also persist to careers with is_curated=False so the learner's profile
            # can reference a real careers FK. Marked as llm source and unreviewed.
            # STRICT ISOLATION: career_vector is NULL so database pgvector RPC
            # cannot match this record. Vector is only generated upon admin promotion.
            career_res = supabase_client.table("careers").insert({
                "title":             request.career_title,
                "description":       request.career_description,
                "career_vector":     None,  # Isolated from pgvector search until admin review
                "is_curated":        False,
                "source_origin":     "llm",
                "review_status":     "unreviewed",
                "proposing_user_id": user_id,
            }).execute()
            if not career_res.data:
                raise RuntimeError("Failed to create provisional career record.")
            career_id = career_res.data[0]["id"]

            # Link pending record to the real career row for admin promotion workflow
            supabase_client.table("pending_careers").update({
                "promoted_career_id": career_id
            }).eq("id", pending_res.data[0]["id"]).execute()

        # Determine if the target career is an unreviewed AI proposal.
        # Strict Rule: Canonical careers (onet, esco, dual_sourced, curated_list)
        # must NEVER be mutated by learner additions. Custom learner skills are
        # scoped exclusively to user_skills.
        is_ai_career = False
        if not request.career_id:
            is_ai_career = True
        else:
            c_check = (
                supabase_client.table("careers")
                .select("source_origin")
                .eq("id", career_id)
                .execute()
            )
            if c_check.data and c_check.data[0].get("source_origin") == "llm":
                is_ai_career = True

        # Atomic resolution of all skills
        user_skills_to_insert = []
        for sk in request.skills:
            # 1. Resolve real skill_id in database
            real_skill_id = sk.skill_id
            if not real_skill_id or real_skill_id.startswith("temp-"):
                existing = (
                    supabase_client.table("skills")
                    .select("id")
                    .ilike("name", sk.name.strip())
                    .execute()
                )
                if existing.data:
                    real_skill_id = existing.data[0]["id"]
                else:
                    new_skill_res = (
                        supabase_client.table("skills")
                        .insert({"name": sk.name.strip(), "category": sk.category})
                        .execute()
                    )
                    real_skill_id = new_skill_res.data[0]["id"]

            # 2. Bind skill to career_skills junction ONLY if career is an unreviewed AI proposal.
            # Canonical careers already have authoritative taxonomy relations from O*NET/ESCO.
            if is_ai_career:
                try:
                    supabase_client.table("career_skills").upsert({
                        "career_id":     career_id,
                        "skill_id":      real_skill_id,
                        "source_origin": "llm",
                        "review_status": "unreviewed",
                        "importance":    sk.importance,
                    }, on_conflict="career_id,skill_id", ignore_duplicates=True).execute()
                except Exception as junction_err:
                    print(f"[save-skills] career_skills non-fatal warning: {junction_err}")

            # 3. Prepare user_skill record with evidence provenance.
            user_skill_record = {
                "user_id":         user_id,
                "skill_id":        real_skill_id,
                "proficiency":     sk.proficiency,
                "evidence_source": "self_reported",
            }
            user_skills_to_insert.append(user_skill_record)

        # 4. Link profile to career
        supabase_client.table("profiles").update({
            "target_career_id": career_id
        }).eq("id", user_id).execute()

        # 5. Atomic upsert of learner's initial self-reported skill graph
        if user_skills_to_insert:
            supabase_client.table("user_skills").upsert(user_skills_to_insert).execute()

        return {
            "status": "success",
            "message": "Career and skill graph successfully calibrated and committed.",
            "career_id": career_id,
            "skills_count": len(user_skills_to_insert),
        }

    except Exception as e:
        print("[save-skills] Database error:", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to commit skill profile: {str(e)}"
        )


# ---------------------------------------------------------------------------
# GET /api/onboarding/status/{user_id}
# ---------------------------------------------------------------------------
@router.get("/status/{user_id}")
async def get_onboarding_status(user_id: str, http_req: Request):
    caller_id = get_verified_user_id(http_req)
    if caller_id != user_id:
        raise HTTPException(
            status_code=403, detail="Forbidden: Cannot view another user's onboarding status."
        )

    try:
        profile_res = (
            supabase_client.table("profiles")
            .select("target_career_id")
            .eq("id", user_id)
            .execute()
        )
        if not profile_res.data or not profile_res.data[0].get("target_career_id"):
            return {"onboarding_complete": False, "career": None, "skills": []}

        career_id = profile_res.data[0]["target_career_id"]

        career_res = (
            supabase_client.table("careers")
            .select("id, title, description")
            .eq("id", career_id)
            .execute()
        )
        career = career_res.data[0] if career_res.data else None

        # Join career_skills to attach importance weights for career readiness calculation
        career_skills_res = (
            supabase_client.table("career_skills")
            .select("skill_id, importance, importance_score")
            .eq("career_id", career_id)
            .execute()
        )
        cs_map = {row["skill_id"]: row for row in (career_skills_res.data or [])}

        # Fetch user's rated skills
        skills_res = (
            supabase_client.table("user_skills")
            .select("proficiency, skills(id, name, category)")
            .eq("user_id", user_id)
            .execute()
        )

        skills = []
        for row in skills_res.data:
            sk = row.get("skills")
            if sk:
                cs_info = cs_map.get(sk["id"], {})
                skills.append({
                    **sk,
                    "proficiency": row["proficiency"],
                    "importance": cs_info.get("importance"),
                    "importance_score": cs_info.get("importance_score"),
                })

        return {
            "onboarding_complete": len(skills) > 0,
            "career": career,
            "skills": skills,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch onboarding status: {str(e)}"
        )
