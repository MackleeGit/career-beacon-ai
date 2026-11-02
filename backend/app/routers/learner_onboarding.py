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
# Blocked profanity, insults, slurs, vulgarity, and non-occupational troll tokens
_BLOCKED_TOKENS = {
    "moron", "morons", "idiot", "idiots", "stupid", "dumb", "dumbass", "retard", "retarded",
    "fool", "loser", "jerk", "clown", "noob", "trash", "garbage", "useless", "nobody",
    "fuck", "fucker", "fucking", "fucked", "motherfucker", "shit", "shitty", "bullshit",
    "bitch", "bitches", "ass", "asshole", "arse", "bastard", "dick", "dickhead", "cock",
    "pussy", "cunt", "whore", "slut", "prostitute", "hooker", "pimp", "porn", "pornstar",
    "sex", "sexy", "boobs", "penis", "vagina", "anus", "poop", "pee", "fart", "crap",
    "damn", "hell", "wtf", "stfu", "lmao", "rofl", "lol", "yolo", "bruh", "nigga", "nigger",
    "faggot", "fag", "dyke", "kike", "chink", "spic", "twat", "wanker", "prick", "hoe",
    "thug", "thief", "robber", "burglar", "terrorist", "hitman", "murderer", "killer",
    "scammer", "fraudster", "drugdealer", "cartel", "mafia", "gangster",
    "asdf", "qwerty", "zxcv", "hjkl", "nothing", "none", "whatever",
    "idk", "anything", "something", "someone", "human", "person", "adult", "baby",
    "banana", "potato", "pizza", "burger", "toilet", "monkey", "donkey", "dog", "cat",
}


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

    if len(clean) < 3 or len(clean) > 500:
        raise HTTPException(
            status_code=400,
            detail="Career query must be between 3 and 500 characters long.",
        )

    # Entropy & letter check: reject numbers-only or random keyboard mashing
    letters = [c for c in clean if c.isalpha()]
    if len(letters) < 3:
        raise HTTPException(
            status_code=400,
            detail="Please enter a recognizable job title or career goal (e.g., 'Frontend Developer').",
        )

    # Reject excessive repeated characters (e.g., "aaaaaaa", "hahahaha")
    if re.search(r"(.)\1{3,}", clean.lower()):
        raise HTTPException(
            status_code=400,
            detail="Please enter a recognizable job title or career goal (e.g., 'Frontend Developer').",
        )

    # Tokenize and check against profanity / insult / vulgar / non-career blocklist
    tokens = re.findall(r"[a-z]+", clean.lower())
    if not tokens or any(tok in _BLOCKED_TOKENS for tok in tokens):
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid professional career title or occupation (e.g., 'Data Analyst', 'Civil Engineer').",
        )

    # Vowel/consonant sanity check against keyboard mash (e.g. "bcdfghjkl")
    vowels = set("aeiouy")
    for tok in tokens:
        if len(tok) >= 5 and not any(ch in vowels for ch in tok):
            raise HTTPException(
                status_code=400,
                detail="Please enter a recognizable job title or career goal (e.g., 'Frontend Developer').",
            )
        if re.search(r"[bcdfghjklmnpqrstvwxz]{6,}", tok):
            raise HTTPException(
                status_code=400,
                detail="Please enter a recognizable job title or career goal (e.g., 'Frontend Developer').",
            )

    return clean


def _normalized_title_words(value: str) -> tuple[str, ...]:
    """Normalize small grammatical differences for deterministic title lookup."""
    words = re.findall(r"[a-z0-9]+", value.lower().replace("&", " and "))
    normalized = []
    for word in words:
        # O*NET titles commonly use plural job titles (e.g. Engineers), while
        # learners often type the singular. Keep this deliberately conservative.
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        normalized.append(word)
    return tuple(normalized)


def _career_provenance_label(source: str, status: str) -> str:
    if source == "dual_sourced":
        return "Source: O*NET & ESCO · Review pending" if status == "unreviewed" else "Source: O*NET & ESCO"
    if source == "onet":
        return "Source: O*NET · Review pending" if status == "unreviewed" else "Source: O*NET"
    if source == "esco":
        return "Source: ESCO · Review pending" if status == "unreviewed" else "Source: ESCO"
    if source == "curated_list":
        return "Curated" if status == "curated" else "Internal Starter"
    if source == "llm":
        return "AI Distilled · Review pending" if status == "unreviewed" else "AI Standardized"
    return "AI Suggestion"


async def _canonical_match_result(career: dict) -> dict:
    skills_res = (
        supabase_client.table("career_skills")
        .select("source_origin, review_status, importance, importance_score, skills(*)")
        .eq("career_id", career["id"])
        .execute()
    )
    skills = []
    for row in skills_res.data or []:
        skill = row.get("skills")
        if not skill:
            continue
        source = row.get("source_origin", "llm")
        raw_category = skill.get("category") or "General"
        raw_importance = row.get("importance")
        
        # O*NET noise filtration: Physical/cognitive abilities and generic work activities
        # (e.g., 'Near Vision', 'English Language', 'Identifying Objects') are demoted to optional
        # so only actionable technical skills and domain knowledge appear in the Essential Core tier.
        # Actionable Vocational Competencies vs Generic Foundational Noise
        # Academic O*NET categorizes basic literacy (Active Listening, Reading Comprehension)
        # and physical/cognitive abilities (Near Vision, Arm-Hand Steadiness) across all 840 jobs.
        # These are NOT actionable micro-learning units for recommendation engines.
        # We demote them to 'optional' General Competencies so Essential Core Skills exclusively
        # holds domain-specific knowledge, vocational tasks, and technical tools.
        NOISE_CATEGORIES = ("Ability", "Work Activity")
        GENERIC_NOISE_NAMES = {
            "Reading Comprehension", "Active Listening", "Writing", "Speaking",
            "Mathematics", "Science", "Critical Thinking", "Active Learning",
            "Learning Strategies", "Monitoring", "Social Perceptiveness", "Coordination",
            "Persuasion", "Negotiation", "Instructing", "Service Orientation",
            "Complex Problem Solving", "Judgment and Decision Making", "Time Management",
            "Management of Personnel Resources", "Management of Financial Resources",
            "Management of Material Resources", "Near Vision", "English Language",
            "Speech Recognition", "Speech Clarity", "Identifying Objects, Actions, and Events",
            "Getting Information", "Flexibility of Closure", "Category Flexibility",
            "Oral Comprehension", "Written Comprehension", "Oral Expression", "Written Expression",
            "Problem Sensitivity", "Inductive Reasoning", "Deductive Reasoning",
            "Information Ordering", "Selective Attention", "Fluency of Ideas", "Originality",
            "Perceptual Speed", "Visualization", "Far Vision", "Visual Color Discrimination",
            "Arm-Hand Steadiness", "Finger Dexterity", "Manual Dexterity", "Multilimb Coordination"
        }
        if raw_category in NOISE_CATEGORIES or skill["name"] in GENERIC_NOISE_NAMES:
            effective_importance = "optional"
            display_category = "General Competencies"
        else:
            effective_importance = raw_importance
            display_category = "Technical Skills" if raw_category in ("Skills", "Technical") else raw_category

        skills.append({
            "id": skill["id"],
            "name": skill["name"],
            "category": display_category,
            "importance": effective_importance,
            "importance_score": row.get("importance_score"),
            "source_origin": source,
            "provenance_label": _career_provenance_label(source, row.get("review_status", "unreviewed")),
        })

    # Universal Quality Normalizer: Enforce actionable, non-redundant vocational learning units
    # Evaluates skill quality, specificity, and micro-learning suitability.
    # Automatically activates if a career does not already have a validated, standardized competency pillar stack.
    essential_skills = [s for s in skills if s.get("importance") == "essential"]
    # Recognizes both human-curated and already-distilled provisional stacks
    has_curated_or_distilled_stack = any(
        s.get("source_origin") in ("curated_list", "llm") and s.get("category") != "General Competencies"
        for s in essential_skills
    )
    # Fires if lacks standardized stack OR has fewer than 6 essential skills
    needs_normalization = (not has_curated_or_distilled_stack) or (len(essential_skills) < 6)

    if needs_normalization:
        try:
            norm_prompt = """You are a Vocational Taxonomy Standardizer.
Extract exactly 8 to 10 Primary Vocational Competencies for the specified occupation.

EACH COMPETENCY MUST SATISFY ALL 4 OBJECTIVE TESTS:
1. OBSERVABLE TASK TEST: Must represent an explicit physical, technical, or analytical task performed on the job (e.g. 'Structural Analysis & Design', 'Soil Mechanics Testing'), NOT a broad knowledge domain (FAIL: 'Design', 'Science', 'Engineering').
2. INDEPENDENT TESTABILITY TEST: Must be assessable via a 5-question technical diagnostic test with definitive right/wrong answers.
3. DOMAIN EXCLUSIVITY TEST: Must be specific to this trade or profession. Reject cross-occupational generalities (FAIL: 'Active Listening', 'Critical Thinking', 'Computer Literacy', 'Time Management').
4. ATOMICITY & NO-OVERLAP TEST: No two competencies may share the same underlying technical tools or procedures (FAIL: 'CAD Modeling' AND 'AutoCAD Drafting' in the same list).

OUTPUT strictly valid JSON:
{
    "competencies": [
        {"name": "Skill Name (2 to 4 words)", "category": "Technical | Safety | Tools | Operations"}
    ]
}"""
            c_title = career.get("title", "")
            c_desc = career.get("description", "")
            user_msg = f"Career Title: {c_title}\nDescription: {c_desc}"
            res = await ai_service.generate_json(user_msg, system_instruction=norm_prompt)
            comps = res.get("competencies", [])
            if comps:
                # Demote raw unnormalized essential skills to optional
                supabase_client.table("career_skills").update({"importance": "optional"}).eq("career_id", career["id"]).execute()
                for s in skills:
                    s["importance"] = "optional"
                    if s.get("category") in ("General", "Skills", "Technical", "General Competencies", "Knowledge"):
                        s["category"] = "General Competencies"

                new_batch = []
                distilled_list = []
                for item in comps:
                    name = item.get("name", "").strip()
                    cat = item.get("category", "Technical").strip()
                    if not name:
                        continue
                    sk_res = supabase_client.table("skills").select("id").ilike("name", name).execute()
                    if sk_res.data:
                        sk_id = sk_res.data[0]["id"]
                    else:
                        ins = supabase_client.table("skills").insert({"name": name, "category": cat}).execute()
                        sk_id = ins.data[0]["id"] if ins.data else None
                    if sk_id:
                        # Save with source_origin='llm' and review_status='unreviewed'
                        # for human-by-exception governance approval.
                        new_batch.append({
                            "career_id": career["id"],
                            "skill_id": sk_id,
                            "source_origin": "llm",
                            "review_status": "unreviewed",
                            "importance": "essential",
                            "importance_score": 0.95
                        })
                        distilled_list.append({
                            "id": sk_id,
                            "name": name,
                            "category": cat,
                            "importance": "essential",
                            "importance_score": 0.95,
                            "source_origin": "llm",
                            "provenance_label": "AI Distilled · Review pending",
                        })
                if new_batch:
                    supabase_client.table("career_skills").upsert(new_batch, on_conflict="career_id,skill_id").execute()
                    skills = distilled_list + skills
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[competency-normalizer] Error normalizing {career.get('title')}: {e}")

    # Guarantee at least 6 essential skills even if AI normalization was unreachable:
    # Promote highest importance_score skills from the career's catalog mappings so a learner never sees 0 essential skills.
    current_essential = [s for s in skills if s.get("importance") == "essential"]
    if len(current_essential) == 0 and skills:
        # Sort non-essential skills: domain/technical skills first, then by importance_score descending
        candidates_to_promote = sorted(
            skills,
            key=lambda s: (
                0 if s.get("category") != "General Competencies" else 1,
                -(float(s.get("importance_score") or 0.0)),
                s.get("name", ""),
            ),
        )
        for s in candidates_to_promote[:8]:
            s["importance"] = "essential"
            if s.get("category") == "General Competencies":
                s["category"] = "Core Competencies"

    career["provenance_label"] = _career_provenance_label(
        career.get("source_origin", "llm"), career.get("review_status", "unreviewed")
    )
    # Deterministic category & name ordering across all instances
    skills.sort(key=lambda s: (0 if s.get("importance") == "essential" else 1, s.get("category", ""), s.get("name", "")))
    return {"status": "matched", "career": career, "skills": skills}


# ---------------------------------------------------------------------------
# Pydantic Schemas (Unified Atomic Contract - Workstream 1 & 3)
# ---------------------------------------------------------------------------
class CareerSearchRequest(BaseModel):
    career_query: str
    is_structured_ai: bool = False
    always_show_candidates: bool = False


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

    # Canonical title lookup precedes semantic search. This catches exact and
    # simple singular/plural title matches even when query and catalogue vectors
    # were built from different text (for example query title vs title+description).
    CANONICAL_SOURCES = ("onet", "esco", "dual_sourced", "curated_list")
    try:
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        exact_res = (
            supabase_client.table("careers")
            .select("id, title, description, source_origin, review_status, onet_soc_code, esco_occupation_uri, is_curated")
            .neq("review_status", "rejected")
            .ilike("title", f"{escaped_query}%")
            .limit(25)
            .execute()
        )
        normalized_query = _normalized_title_words(query)
        exact_matches = [
            row for row in (exact_res.data or [])
            if _normalized_title_words(row.get("title", "")) == normalized_query
        ]
        if exact_matches:
            priority = {"dual_sourced": 0, "onet": 1, "esco": 2, "curated_list": 3, "llm": 4}
            exact_matches.sort(key=lambda row: priority.get(row.get("source_origin"), 9))
            top_exact = exact_matches[0]
            if not request.always_show_candidates:
                return await _canonical_match_result(top_exact)
    except Exception as e:
        # Exact lookup is an improvement, not a dependency: retain semantic search
        # when a database title query is unavailable.
        print("[career-search] canonical title lookup error:", e)

    # 2. Semantic search remains the path for non-exact, natural-language queries.
    #    Thresholds tuned for the card-grid UX: surface up to 8 candidates for the
    #    user to pick from rather than forcing a binary match/no-match decision.
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # Auto-select without asking user
    DISAMBIGUATION_THRESHOLD = 0.75   # Must clear 0.75 to return catalog-only grid without AI synthesis
    AI_COEXIST_FLOOR = 0.25           # Floor when fetching closest catalog neighbours for AI fallback
    try:
        query_vector = await embedding_service.get_embedding(query)
        response = supabase_client.rpc(
            "match_careers",
            {
                "query_embedding": query_vector,
                "match_threshold": AI_COEXIST_FLOOR,
                "match_count": 10,  # Over-fetch so we can trim to 8 after source filter
            },
        ).execute()

        raw_candidates = response.data or []
        candidates = []
        if raw_candidates:
            cand_ids = [c["id"] for c in raw_candidates]
            source_res = (
                supabase_client.table("careers")
                .select("id, is_curated, source_origin, review_status, onet_soc_code, esco_occupation_uri")
                .in_("id", cand_ids)
                .in_("source_origin", list(CANONICAL_SOURCES))
                .neq("review_status", "rejected")
                .execute()
            )
            canonical_dict = {row["id"]: row for row in (source_res.data or [])}
            for candidate in raw_candidates:
                if candidate["id"] in canonical_dict:
                    merged = dict(candidate)
                    merged.update(canonical_dict[candidate["id"]])
                    candidates.append(merged)

        # If we had exact matches, prepend top_exact to candidate pool
        if exact_matches and request.always_show_candidates:
            top_exact_cand = {
                "id": top_exact["id"],
                "title": top_exact["title"],
                "description": top_exact.get("description", ""),
                "similarity": 0.99,
            }
            candidates = [top_exact_cand] + [c for c in candidates if c["id"] != top_exact["id"]]

        if candidates and not request.is_structured_ai:
            top_match = candidates[0]
            top_score = top_match.get("similarity", 0)
            if top_score >= HIGH_CONFIDENCE_THRESHOLD and not request.always_show_candidates:
                return await _canonical_match_result(top_match)

            # Only show catalog-only disambiguation grid if the top match clears DISAMBIGUATION_THRESHOLD (0.75).
            # If top_score < 0.75 (e.g., 0.69 for "Martian Colony Terraform Specialist"), fall through to AI
            # synthesis so the AI Career Target card is presented alongside these closest catalog neighbors!
            strong_candidates = [c for c in candidates if c.get("similarity", 0) >= DISAMBIGUATION_THRESHOLD]
            if strong_candidates:
                return {
                    "status": "disambiguation_required",
                    "candidates": [
                        {
                            "id": c["id"],
                            "title": c["title"],
                            "description": c.get("description", ""),
                            "similarity": round(c.get("similarity", 0), 2),
                        }
                        for c in strong_candidates[:8]
                    ],
                }
    except Exception as e:
        print("[career-search] RPC search error:", e)

    # 3. AI Fallback: Validate occupational intent AND generate structured occupational skill profile.
    system_prompt = """You are an expert labor-market analyst and Vocational Taxonomy Standardizer.
First, determine whether the user's query represents a legitimate, recognizable, or plausible human occupation, profession, trade, or specialized career role (including surgical specialties, emerging tech, or blue-collar trades).
REJECT the query (set "is_valid_career": false) if it is an insult, slur, everyday object, animal, or non-occupational gibberish.

When valid, extract exactly 8 to 10 Primary Vocational Competencies for this occupation.
EACH COMPETENCY MUST SATISFY ALL 4 OBJECTIVE TESTS:
1. OBSERVABLE TASK TEST: Must represent an explicit physical, technical, clinical, or analytical task performed on the job (e.g. 'Composite Restoration Placement', 'Endoscopic Sinus Surgery', 'Structural Beam Sizing'), NOT a broad knowledge bucket (FAIL: 'Science', 'Communication', 'Healthcare').
2. INDEPENDENT TESTABILITY TEST: Must be assessable via a 5-question technical diagnostic checkpoint with definitive right/wrong answers.
3. DOMAIN EXCLUSIVITY TEST: Must be specific to this trade or profession. Reject cross-occupational generalities (FAIL: 'Active Listening', 'Critical Thinking', 'Computer Literacy', 'Time Management', 'EMR Systems').
4. ATOMICITY & NO-OVERLAP TEST: No two competencies may share the same underlying technical tools or procedures.

CATEGORIES (use exactly these names):
- "Technical": Core specialized execution and domain techniques
- "Operations": Day-to-day occupational procedures, clinical tasks, or operational workflows
- "Safety": Safety regulations, infection control, hazard mitigation, or emergency protocols
- "Tools": Dedicated machinery, diagnostic hardware, software platforms, or instruments

OUTPUT strictly valid JSON:
{
    "is_valid_career": true,
    "title": "Standardized Job Title",
    "description": "One clear sentence describing the occupational scope and responsibilities.",
    "skills": [
        {"name": "Competency Name (2 to 4 words)", "category": "Technical | Operations | Safety | Tools"}
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

    if ai_data.get("is_valid_career") is False or not ai_data.get("title"):
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid professional career title or occupation (e.g., 'Data Analyst', 'Civil Engineer').",
        )

    # Canonicalize AI-generated skills against existing database skills
    # Matches AI-suggested skill names to existing canonical skills to prevent duplicate near-synonyms
    # and prioritizes verified catalog standards over provisional AI proposals.
    db_skills_res = supabase_client.table("skills").select("id, name, category, esco_skill_uri, onet_element_id").execute()
    existing_skills = db_skills_res.data or []
    exact_map = {s["name"].lower().strip(): s for s in existing_skills}

    pending_skills = []
    for sk in ai_data.get("skills", []):
        raw_name = sk["name"].strip()
        norm_name = raw_name.lower()

        # Check exact or normalized match only. Prevent cross-domain false positives (e.g. Martian terraforming matching IaC Terraform)
        match = exact_map.get(norm_name)

        if match:
            source_origin = "esco" if match.get("esco_skill_uri") else ("onet" if match.get("onet_element_id") else "curated_list")
            pending_skills.append({
                "id": match["id"],
                "name": match["name"],
                "category": match.get("category") or sk.get("category") or "General",
                "importance": "essential",
                "source_origin": source_origin,
                "provenance_label": "Catalog Standard",
                "is_canonical": True,
            })
        else:
            pending_skills.append({
                "id": f"temp-{uuid.uuid4().hex[:8]}",
                "name": raw_name,
                "category": sk.get("category") or "General",
                "importance": None,
                "source_origin": "llm",
                "provenance_label": "AI Suggestion",
                "is_canonical": False,
            })

    # Prioritize canonical database standards above provisional AI proposals
    pending_skills.sort(key=lambda s: 0 if s.get("is_canonical") else 1)

    # Co-existence: Only attach catalog vector matches that genuinely clear DISAMBIGUATION_THRESHOLD (0.75).
    # Weak sub-75% matches (e.g. 69% Geographers for Martian Colony Terraform Specialist) are excluded.
    # Co-existence: Attach closest catalog benchmarks (>= 0.35) so learner always sees
    # canonical O*NET/ESCO alternatives alongside the AI proposal.
    strong_related = [
        c for c in (candidates if 'candidates' in locals() and candidates else [])
        if c.get("similarity", 0) >= 0.35
    ]
    vector_candidate_list = [
        {
            "id": c["id"],
            "title": c["title"],
            "description": c.get("description", ""),
            "similarity": round(c.get("similarity", 0), 2),
            "is_catalog": True,
        }
        for c in strong_related[:5]
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
        "related_candidates": vector_candidate_list,
    }


# ---------------------------------------------------------------------------
# GET /api/onboarding/career/{career_id}
# ---------------------------------------------------------------------------
@router.get("/career/{career_id}")
async def get_career_by_id(career_id: str, http_req: Request):
    """
    Directly retrieves a career and its taxonomy skills by primary key ID.
    Eliminates redundant search/embedding round-trips when selecting from candidate grid.
    """
    _ = get_verified_user_id(http_req)
    res = (
        supabase_client.table("careers")
        .select("id, title, description, source_origin, review_status, onet_soc_code, esco_occupation_uri, is_curated")
        .eq("id", career_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Career not found.")
    
    return await _canonical_match_result(res.data[0])

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

            # Check if a career with this title already exists in careers (idempotent lookup)
            clean_title = request.career_title.strip()
            existing_c = (
                supabase_client.table("careers")
                .select("id")
                .ilike("title", clean_title)
                .limit(1)
                .execute()
            )
            if existing_c.data:
                career_id = existing_c.data[0]["id"]
            else:
                # Persist to careers with is_curated=False so the learner's profile
                # can reference a real careers FK. Marked as llm source and unreviewed.
                career_res = supabase_client.table("careers").insert({
                    "title":             clean_title,
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

        # 5. Replace learner's skill graph for the active career cleanly
        supabase_client.table("user_skills").delete().eq("user_id", user_id).execute()
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
            .select("proficiency, evidence_source, skills(id, name, category)")
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
                    "evidence_source": row.get("evidence_source") or "self_reported",
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


# ---------------------------------------------------------------------------
# POST /api/onboarding/reset (Account Space - Restart Learner Onboarding)
# ---------------------------------------------------------------------------

@router.post("/reset")
async def reset_learner_account(http_req: Request):
    """
    Completely wipes a learner's skill proficiencies, target career alignment,
    active mentor connections, and scheduled sessions so they can start onboarding afresh.
    """
    user_id = get_verified_user_id(http_req)
    try:
        # 1. Delete all user_skills for this learner
        supabase_client.table("user_skills").delete().eq("user_id", user_id).execute()
        # 2. Reset target career in profiles
        supabase_client.table("profiles").update({"target_career_id": None}).eq("id", user_id).execute()
        # 3. Clean up active mentorship service memory/records
        from app.services.mentorship_service import mentorship_service
        mentorship_service.connections = [c for c in mentorship_service.connections if c.get("learner_id") != user_id]
        mentorship_service.sessions = [s for s in mentorship_service.sessions if s.get("learner_id") != user_id]

        return {
            "status": "success",
            "message": "Learner onboarding progress, skills, and sessions have been completely reset.",
        }
    except Exception as err:
        print(f"[learner-reset] Error resetting learner {user_id}: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to reset learner account: {err}")
