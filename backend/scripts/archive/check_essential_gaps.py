import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

target_careers = [
    "Registered Nurse",
    "Accountant and Auditor",
    "Software Developer",
    "Data Scientist",
    "Mechanical Engineer",
    "Commercial Pilot",
    "Information Security Analyst",
    "Financial and Investment Analyst",
    "Electrician",
    "Paralegal and Legal Assistant",
]

def query_with_retry(fn, max_retries=3, delay=1.5):
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(delay)

# Fetch existing micro_content skill IDs
mc_res = query_with_retry(lambda: supabase_client.table("micro_content").select("associated_skill_id, source_url").execute())
existing_skills = {}
for r in (mc_res.data or []):
    sid = r.get("associated_skill_id")
    if sid:
        existing_skills.setdefault(sid, []).append(r.get("source_url"))

print(f"Total skills with existing content in micro_content: {len(existing_skills)}")

for title in target_careers:
    c_res = query_with_retry(lambda: supabase_client.table("careers").select("id, title").eq("title", title).limit(1).execute())
    if not c_res.data:
        print(f"Career not found: {title}")
        continue
    cid = c_res.data[0]["id"]

    # Fetch essential career skills
    cs_res = query_with_retry(lambda: supabase_client.table("career_skills").select(
        "skill_id, importance, importance_score, tier, rank, skills(id, name, category)"
    ).eq("career_id", cid).eq("importance", "essential").order("tier").order("rank").limit(10).execute())

    rows = cs_res.data or []
    covered = [r for r in rows if r.get("skill_id") in existing_skills]
    missing = [r for r in rows if r.get("skill_id") not in existing_skills]

    print(f"\nCareer: {title}")
    print(f"  Essential skills: {len(rows)} inspected | Covered: {len(covered)} | Missing: {len(missing)}")
    if covered:
        print(f"    * Covered sample: {[c.get('skills', {}).get('name') for c in covered[:3]]}")
    if missing:
        print(f"    * Missing sample: {[m.get('skills', {}).get('name') for m in missing[:3]]}")
