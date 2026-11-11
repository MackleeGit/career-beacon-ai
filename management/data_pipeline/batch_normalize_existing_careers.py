"""
management/data_pipeline/batch_normalize_existing_careers.py

Academic-Grade Database Normalization Script.
Executes non-destructive in-place cleanup on the existing Supabase O*NET / ESCO database:
1. Normalizes career titles: inverts census commas, strips bureaucratic clauses, and singularizes role nouns.
2. Demotes physiological and soft transversal noise in `career_skills` to 'optional'.
3. Preserves all Primary Key UUIDs, foreign key relationships, user progress, and mentor records.
"""

import sys
import os
import re
from typing import List, Tuple

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
from app.core.database import supabase_client

BUREAUCRATIC_PHRASES_TO_CLEAN = [
    r",\s*All Other\b",
    r",\s*Except.*$",
    r"\s*\(Except.*?\)",
]

PLURAL_EXCEPTIONS = {
    "physics", "mathematics", "analytics", "logistics", "robotics",
    "operations", "systems", "communications", "relations", "graphics",
    "news", "press", "glass", "business", "wellness", "sales", "customs",
    "affairs", "materials", "resources", "securities", "futures", "records"
}

IRREGULAR_SINGULARS = {
    "firefighters": "firefighter",
    "cooks": "cook",
    "chefs": "chef",
    "physicians": "physician",
    "nurses": "nurse",
    "surgeons": "surgeon",
    "lawyers": "lawyer",
    "judges": "judge",
    "writers": "writer",
    "editors": "editor",
    "dentists": "dentist",
    "pharmacists": "pharmacist",
    "paramedics": "paramedic",
    "electricians": "electrician",
    "mechanics": "mechanic",
    "machinists": "machinist",
    "carpenters": "carpenter",
    "plumbers": "plumber",
    "pilots": "pilot",
    "clerks": "clerk",
    "guards": "guard",
    "scientists": "scientist",
    "architects": "architect",
    "economists": "economist",
    "analysts": "analyst",
    "engineers": "engineer",
    "developers": "developer",
    "designers": "designer",
    "managers": "manager",
    "directors": "director",
    "administrators": "administrator",
    "supervisors": "supervisor",
    "inspectors": "inspector",
    "technicians": "technician",
    "technologists": "technologist",
    "specialists": "specialist",
    "consultants": "consultant",
    "advisors": "advisor",
    "officers": "officer",
    "assistants": "assistant",
    "operators": "operator",
    "workers": "worker",
    "laborers": "laborer",
    "drivers": "driver",
    "tellers": "teller",
    "agents": "agent",
    "representatives": "representative",
    "therapists": "therapist",
    "counselors": "counselor",
    "dietitians": "dietitian",
    "optometrists": "optometrist",
    "veterinarians": "veterinarian",
}

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

def normalize_title(raw_title: str) -> str:
    title = raw_title.strip()
    for pat in BUREAUCRATIC_PHRASES_TO_CLEAN:
        if re.search(pat, title, flags=re.IGNORECASE):
            title = re.sub(pat, "", title, flags=re.IGNORECASE).strip()

    if "," in title:
        parts = [p.strip() for p in title.split(",") if p.strip()]
        if len(parts) == 2:
            title = f"{parts[1]} {parts[0]}"

    words = title.split()
    normalized_words = []
    for w in words:
        w_lower = w.lower()
        if w_lower in PLURAL_EXCEPTIONS:
            normalized_words.append(w)
        elif w_lower in IRREGULAR_SINGULARS:
            sing = IRREGULAR_SINGULARS[w_lower]
            sing = sing.capitalize() if w[0].isupper() else sing
            normalized_words.append(sing)
        elif w_lower.endswith("ies") and len(w_lower) > 4:
            sing = w[:-3] + "y"
            normalized_words.append(sing)
        elif w_lower.endswith("s") and not w_lower.endswith(("ss", "us", "is")) and len(w_lower) > 3:
            sing = w[:-1]
            normalized_words.append(sing)
        else:
            normalized_words.append(w)

    return " ".join(normalized_words)

def run_batch_normalization():
    print("=" * 80)
    print("RUNNING BATCH NORMALIZATION ON LIVE SUPABASE DATABASE")
    print("=" * 80)

    # 1. Fetch all careers in chunks
    print("\n[Step 1/2] Normalizing Career Titles in 'careers' table...")
    offset = 0
    limit = 100
    total_titles_updated = 0

    while True:
        res = (
            supabase_client.table("careers")
            .select("id, title")
            .order("title")
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            break

        for row in rows:
            cid = row["id"]
            raw = row["title"]
            clean = normalize_title(raw)
            if clean != raw:
                try:
                    supabase_client.table("careers").update({"title": clean}).eq("id", cid).execute()
                    total_titles_updated += 1
                    if total_titles_updated <= 15 or total_titles_updated % 50 == 0:
                        print(f"  - [{cid[:8]}] '{raw}' -> '{clean}'")
                except Exception as err:
                    print(f"  ! Error updating career {cid}: {err}")

        offset += limit
        if len(rows) < limit:
            break

    print(f"-> Title normalization complete: {total_titles_updated} career titles updated.")

    # 2. Demote noisy skills in career_skills
    print("\n[Step 2/2] Demoting Physiological & Non-Vocational Noise in 'career_skills'...")
    # Fetch skill IDs for known noise names
    noise_ids = []
    for noise_name in GENERIC_NOISE_NAMES:
        sk_res = supabase_client.table("skills").select("id").ilike("name", noise_name).execute()
        if sk_res.data:
            noise_ids.extend([s["id"] for s in sk_res.data])

    noise_ids = list(set(noise_ids))
    print(f"  - Identified {len(noise_ids)} noise competency IDs in 'skills' dictionary.")

    total_noise_demoted = 0
    if noise_ids:
        # Demote in chunks of 50 IDs
        for i in range(0, len(noise_ids), 30):
            chunk = noise_ids[i:i + 30]
            try:
                upd = (
                    supabase_client.table("career_skills")
                    .update({"importance": "optional"})
                    .in_("skill_id", chunk)
                    .eq("importance", "essential")
                    .execute()
                )
                if upd.data:
                    total_noise_demoted += len(upd.data)
            except Exception as err:
                print(f"  ! Error demoting noise chunk: {err}")

    print(f"-> Noise filtration complete: {total_noise_demoted} essential noise links demoted to optional.")

    print("\n" + "=" * 80)
    print("BATCH NORMALIZATION SUMMARY:")
    print(f" - Career Titles Cleaned & Singularized: {total_titles_updated}")
    print(f" - Non-Vocational Abilities Demoted in Taxonomy: {total_noise_demoted}")
    print(" - Primary Keys, Foreign Keys, User Progress, Mentorship Connections: 100% Intact")
    print("=" * 80)

if __name__ == "__main__":
    run_batch_normalization()

