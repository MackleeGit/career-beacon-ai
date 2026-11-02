import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService

async def test_secretary_drop():
    # Find Secretary career ID
    c_res = supabase_client.table("careers").select("id, title").ilike("title", "%Secretary%").execute()
    print("Secretary careers:", c_res.data)
    career_id = c_res.data[0]["id"]
    career_title = c_res.data[0]["title"]

    # Find or use learner with Secretary career
    p_res = supabase_client.table("profiles").select("id, email, target_career_id").eq("target_career_id", career_id).execute()
    if p_res.data:
        user_id = p_res.data[0]["id"]
        email = p_res.data[0]["email"]
    else:
        # Pick any test learner
        p_res = supabase_client.table("profiles").select("id, email").eq("role", "learner").limit(1).execute()
        user_id = p_res.data[0]["id"]
        email = p_res.data[0]["email"]
        supabase_client.table("profiles").update({"target_career_id": career_id}).eq("id", user_id).execute()

    print(f"\nTesting Secretary Daily Drop for user: {email} (ID: {user_id})")
    service = DailyDropService()
    drop = await service.get_or_create_daily_drop(user_id)
    print("Target Skill:", drop.get("target_skill_name"))
    print("Lessons count:", len(drop.get("lessons", [])))
    for i, it in enumerate(drop.get("lessons", []), 1):
        print(f"\n  Lesson {i}:")
        print(f"    Title: {it.get('title')}")
        print(f"    Source: {it.get('source_url')}")
        print(f"    Adapter: {it.get('source_adapter')}")
        print(f"    Summary Bullets: {it.get('summary_bullets')[:100]}...")

asyncio.run(test_secretary_drop())
