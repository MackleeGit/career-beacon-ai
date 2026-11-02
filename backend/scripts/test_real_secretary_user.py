import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService

user_id = "f216bf54-ec34-451f-b29e-cec85b3e9f50"
p_res = supabase_client.table("profiles").select("id, email, target_career_id").eq("id", user_id).execute()
print("Profile:", p_res.data)

u_skills = supabase_client.table("user_skills").select("skill_id, skills(id, name)").eq("user_id", user_id).execute()
print(f"Enrolled skills count: {len(u_skills.data or [])}")
for r in (u_skills.data or [])[:5]:
    print("  Skill:", r.get("skills", {}).get("name"))

async def test_user_drop():
    service = DailyDropService()
    drop = await service.get_or_create_daily_drop(user_id)
    print("\nTarget Skill in Drop:", drop.get("target_skill_name"))
    print("Lessons count:", len(drop.get("lessons", [])))
    for i, it in enumerate(drop.get("lessons", []), 1):
        print(f"\n  Lesson {i}:")
        print(f"    Title: {it.get('title')}")
        print(f"    Source: {it.get('source_url')}")
        print(f"    Adapter: {it.get('source_adapter')}")

asyncio.run(test_user_drop())
