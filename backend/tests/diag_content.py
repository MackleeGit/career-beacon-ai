import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client
from app.services.recommendation_service import RecommendationService

async def diag():
    rec = RecommendationService()
    print("--- Checking Frontend Developer skills and micro_content ---")
    fe_user_id = "e955aa77-c9a4-4976-ba6f-a0e6b0edcdf0"
    prof = supabase_client.table("profiles").select("target_career_id").eq("id", fe_user_id).execute()
    career_id = prof.data[0]["target_career_id"]
    career = rec.get_cached_career(career_id)
    print(f"Career: {career.get('title')} ({career_id})")

    user_skills = supabase_client.table("user_skills").select("skill_id, proficiency, skills(id, name)").eq("user_id", fe_user_id).execute()
    for us in user_skills.data:
        sk = us.get("skills")
        sk_id = sk["id"]
        sk_name = sk["name"]
        # Count micro_content with associated_skill_id
        mc_res = supabase_client.table("micro_content").select("id, title, associated_skill_id, quizzes, source_url").eq("associated_skill_id", sk_id).execute()
        # Count micro_content with career_id
        mc_career = supabase_client.table("micro_content").select("id, title, associated_skill_id, quizzes, source_url").eq("career_id", career_id).execute()
        print(f"  Skill: {sk_name} ({sk_id}) -> micro_content by skill: {len(mc_res.data)}, by career: {len(mc_career.data)}")
        if mc_res.data:
            for item in mc_res.data[:2]:
                print(f"    Sample: '{item['title'][:40]}' | quizzes: {bool(item.get('quizzes'))}")

    print("\n--- Checking Attorney skills and micro_content ---")
    atty_user_id = "8adfd80e-fa24-410b-87fc-5ff3307e425d"
    prof_atty = supabase_client.table("profiles").select("target_career_id").eq("id", atty_user_id).execute()
    atty_career_id = prof_atty.data[0]["target_career_id"]
    atty_career = rec.get_cached_career(atty_career_id)
    print(f"Career: {atty_career.get('title')} ({atty_career_id})")
    atty_mc = supabase_client.table("micro_content").select("id, title, associated_skill_id, career_id").eq("career_id", atty_career_id).execute()
    print(f"  Attorney micro_content by career_id: {len(atty_mc.data)}")

if __name__ == "__main__":
    asyncio.run(diag())

