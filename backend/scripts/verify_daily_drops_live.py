import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService

async def test_user(email):
    print(f"\n==========================================")
    print(f"Testing Daily Drop for: {email}")
    res = supabase_client.table("profiles").select("id, full_name, email, role, target_career_id").eq("email", email).execute()
    if not res.data:
        print(f"User {email} not found.")
        return
    profile = res.data[0]
    user_id = profile["id"]
    career_id = profile.get("target_career_id")
    career_title = "None"
    if career_id:
        c_res = supabase_client.table("careers").select("id, title").eq("id", career_id).execute()
        if c_res.data:
            career_title = c_res.data[0]["title"]
            print(f"Career: {career_title} (ID: {career_id})")

    service = DailyDropService()
    drop = await service.get_or_create_daily_drop(user_id)
    if not drop:
        print("Result: No drop returned (None)")
        return

    items = drop.get("lessons") or []
    print(f"Total items in drop: {len(items)}")
    for i, it in enumerate(items, 1):
        title = it.get("title")
        source = it.get("source_url") or it.get("source_name") or "Unknown"
        skill = it.get("skill_name")
        adapter = it.get("source_adapter")
        print(f"  Item {i}:")
        print(f"    Title: {title}")
        print(f"    Skill: {skill}")
        print(f"    Source: {source}")
        print(f"    Adapter: {adapter}")

async def main():
    await test_user("learnereleven@gmail.com")
    await test_user("adamtest@gmail.com")

if __name__ == "__main__":
    asyncio.run(main())
