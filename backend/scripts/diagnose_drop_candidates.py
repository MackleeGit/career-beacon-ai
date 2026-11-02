import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.recommendation_service import RecommendationService, _lesson_matches_career
from app.services.daily_drop_service import DailyDropService

rec_service = RecommendationService()
daily_service = DailyDropService()

for email in ["learnereleven@gmail.com", "adamtest@gmail.com"]:
    print(f"\n--- Diagnosing {email} ---")
    prof_res = supabase_client.table("profiles").select("id, target_career_id").eq("email", email).execute()
    if not prof_res.data:
        print("User not found")
        continue
    user_id = prof_res.data[0]["id"]
    career_id = prof_res.data[0]["target_career_id"]
    career = rec_service.get_cached_career(career_id)
    career_title = career.get("title", "")
    print(f"User ID: {user_id}, Career ID: {career_id}, Title: {career_title}")

    # Check user skills
    u_skills = supabase_client.table("user_skills").select("skill_id, proficiency, skills(id, name)").eq("user_id", user_id).execute()
    print(f"Enrolled skills count: {len(u_skills.data or [])}")
    for row in (u_skills.data or [])[:5]:
        print(f"  Skill: {row.get('skills', {}).get('name')} (ID: {row.get('skill_id')}, Prof: {row.get('proficiency')})")

    # Check career skills
    c_skills = rec_service.get_cached_career_skills(career_id)
    print(f"Career skills count in map: {len(c_skills)}")

    # Check micro_content in database for this career or its skills
    skill_ids = list(c_skills.keys())
    print(f"Career skill IDs sample: {skill_ids[:3]}")
    if skill_ids:
        mc = supabase_client.table("micro_content").select("id, title, associated_skill_id, career_id, source_url").in_("associated_skill_id", skill_ids[:10]).execute()
        print(f"Micro content matching career skills count: {len(mc.data or [])}")
        for m in (mc.data or []):
            matches = _lesson_matches_career(m, career_title)
            print(f"  MC: {m.get('title')[:50]} | matches career '{career_title}': {matches}")

