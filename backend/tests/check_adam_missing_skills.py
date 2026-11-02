import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def check():
    adam_id = "4054e2d2-fa94-4497-8d4f-635610c836d1"
    career_id = "de6cab44-2961-4694-b46e-b38d724db3e3"
    
    # Essential career skills
    cs = supabase_client.table("career_skills").select("skill_id, importance, skills(id, name, category)").eq("career_id", career_id).eq("importance", "essential").execute()
    print(f"Essential skills for Web Developer: {len(cs.data)}")
    essential_ids = {row["skill_id"]: row["skills"]["name"] for row in cs.data if row.get("skills")}
    for sid, sname in essential_ids.items():
        print(f"  - {sname} ({sid})")

    # Adam's enrolled skills
    us = supabase_client.table("user_skills").select("skill_id, proficiency, skills(id, name)").eq("user_id", adam_id).execute()
    adam_skill_ids = {row["skill_id"]: row["skills"]["name"] for row in us.data if row.get("skills")}
    print(f"\nAdam has {len(adam_skill_ids)} skills enrolled.")
    
    # Check overlap
    overlap = set(essential_ids.keys()) & set(adam_skill_ids.keys())
    print(f"Overlap with essential skills: {len(overlap)} / {len(essential_ids)}")
    for sid in overlap:
        print(f"  Enrolled essential: {essential_ids[sid]}")
    missing = set(essential_ids.keys()) - set(adam_skill_ids.keys())
    print(f"Missing essential skills for Adam: {len(missing)}")
    for sid in missing:
        print(f"  MISSING: {essential_ids[sid]}")

if __name__ == "__main__":
    check()

