import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService, DAILY_SPRINTS_FILE, _load_json_file, _today_str

user_id = "9c4d483e-1296-4c24-8a78-fb09b2e30181"
today = _today_str()
sprints = _load_json_file(DAILY_SPRINTS_FILE)
existing = next(
    (s for s in sprints if s.get("user_id") == user_id and s.get("sprint_date") == today),
    None
)
print("Today string:", today)
print("Existing in sprints:", existing)

async def test_step_by_step():
    service = DailyDropService()
    if existing:
        print("\nExisting found! Hydrating...")
        hydrated = await service._hydrate_drop(existing, user_id)
        print("Hydrated lessons count:", len(hydrated.get("lessons", [])))
        print("Hydrated target skill:", hydrated.get("target_skill_name"))
        print("Is completed:", hydrated.get("is_completed"))

        prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
        cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
        print("User target_career_id in DB:", cid)
        
        # Check condition in daily_drop_service
        if hydrated.get("lessons") and len(hydrated["lessons"]) >= 3:
            print("Condition (len >= 3) was MET!")
        else:
            print("Condition (len >= 3) was NOT MET! So it would purge from sprints list.")

    print("\nCalling get_or_create_daily_drop directly...")
    drop = await service.get_or_create_daily_drop(user_id)
    print("Drop result target skill:", drop.get("target_skill_name"))
    print("Drop result lessons count:", len(drop.get("lessons", [])))

asyncio.run(test_step_by_step())

