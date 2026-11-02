import os
import sys

path = os.path.join(os.path.dirname(__file__), "..", "app", "routers", "learner_onboarding.py")
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Exact title lookup in search_career: remove restrictive source_origin filter
old_exact = """        escaped_query = query.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")
        exact_res = (
            supabase_client.table("careers")
            .select("id, title, description, source_origin, review_status, onet_soc_code, esco_occupation_uri, is_curated")
            .in_("source_origin", list(CANONICAL_SOURCES))
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
            priority = {"dual_sourced": 0, "onet": 1, "esco": 2, "curated_list": 3}"""

new_exact = """        escaped_query = query.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")
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
            priority = {"dual_sourced": 0, "onet": 1, "esco": 2, "curated_list": 3, "llm": 4}"""

if old_exact in code:
    code = code.replace(old_exact, new_exact, 1)
    print("Step 1 (exact lookup) patched.")
else:
    print("Error: Step 1 target not found.")
    sys.exit(1)

# 2. Harmonize prompt in search_career to use the exact 4-test vocational rubric
old_prompt = """    system_prompt = \"\"\"You are an expert labor-market analyst and occupational gatekeeper.
First, determine whether the user's query represents a legitimate, recognizable, or plausible human occupation, profession, trade, or specialized career role (including emerging or futuristic roles like 'Martian Colony Terraform Specialist').
REJECT the query (set "is_valid_career": false) if it is:
- An insult, slur, profanity, vulgarity, or derogatory term (e.g. 'moron', 'idiot', 'clown')
- A random everyday object, food, animal, or non-occupational noun (e.g. 'table', 'banana')
- Gibberish, keyboard mashing, or a vague non-career phrase (e.g. 'get rich quick', 'idk')

DOMAIN CATEGORIES (use exactly these names when valid):
- "Technical Skills": core technical abilities (e.g. programming languages, algorithms, data analysis)
- "Domain Knowledge": subject-matter expertise specific to the field (e.g. financial modeling, network protocols)
- "Tools & Systems": specific software, platforms, or frameworks used daily (e.g. React, PostgreSQL, Docker)
- "Interpersonal & Leadership": communication, collaboration, or management abilities

RULES:
- Include 6-10 skills total across all categories when valid.
- Only include skills clearly backed by job market demand for this specific role.
- Do NOT invent prerequisite relationships or tier numbers.

OUTPUT strictly valid JSON:
{
    "is_valid_career": true,
    "title": "Standardized Job Title",
    "description": "One clear sentence describing the role.",
    "skills": [
        {"name": "Skill Name", "category": "Technical Skills"},
        {"name": "Skill Name", "category": "Tools & Systems"}
    ]
}\"\"\""""

new_prompt = """    system_prompt = \"\"\"You are an expert labor-market analyst and Vocational Taxonomy Standardizer.
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
}\"\"\""""

if old_prompt in code:
    code = code.replace(old_prompt, new_prompt, 1)
    print("Step 2 (harmonized prompt) patched.")
else:
    print("Error: Step 2 target not found.")
    sys.exit(1)

# 3. strong_related threshold: lowered to 0.35 so closest catalog alternatives are always passed!
old_strong = """    strong_related = [
        c for c in (candidates if 'candidates' in locals() and candidates else [])
        if c.get("similarity", 0) >= DISAMBIGUATION_THRESHOLD
    ]"""

new_strong = """    # Co-existence: Attach closest catalog benchmarks (>= 0.35) so learner always sees
    # canonical O*NET/ESCO alternatives alongside the AI proposal.
    strong_related = [
        c for c in (candidates if 'candidates' in locals() and candidates else [])
        if c.get("similarity", 0) >= 0.35
    ]"""

if old_strong in code:
    code = code.replace(old_strong, new_strong, 1)
    print("Step 3 (strong_related threshold) patched.")
else:
    print("Error: Step 3 target not found.")
    sys.exit(1)

# 4. save-skills: Prevent duplicate key violation by checking existing careers before insert!
old_save = """            # Also persist to careers with is_curated=False so the learner's profile
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
            career_id = career_res.data[0]["id"]"""

new_save = """            # Check if a career with this title already exists in careers (idempotent lookup)
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
                career_id = career_res.data[0]["id"]"""

if old_save in code:
    code = code.replace(old_save, new_save, 1)
    print("Step 4 (save-skills duplicate key fix) patched.")
else:
    print("Error: Step 4 target not found.")
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("SUCCESS: learner_onboarding.py successfully updated across all 4 systemic areas!")
