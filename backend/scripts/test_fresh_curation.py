import os
import sys
import json
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService, DAILY_SPRINTS_FILE, _load_json_file, _save_json_file
from app.services.recommendation_service import _lesson_matches_career

# Remove all existing sprints for adamtest and learnereleven from daily_sprints.json
sprints = _load_json_file(DAILY_SPRINTS_FILE)
target_emails = ["adamtest@gmail.com", "learnereleven@gmail.com"]
res = supabase_client.table("profiles").select("id, email").in_("email", target_emails).execute()
user_ids = {r["email"]: r["id"] for r in (res.data or [])}

print("User IDs:", user_ids)
filtered_sprints = [s for s in sprints if s.get("user_id") not in user_ids.values()]
print(f"Removed {len(sprints) - len(filtered_sprints)} stale sprints.")
_save_json_file(DAILY_SPRINTS_FILE, filtered_sprints)

# Now test fresh curation for adamtest
async def test_fresh():
    service = DailyDropService()
    print("\n--- Fresh Curation for adamtest ---")
    adam_id = user_ids.get("adamtest@gmail.com")
    drop = await service.get_or_create_daily_drop(adam_id)
    print("Adam's Target Skill:", drop.get("target_skill_name"))
    print("Adam's Lessons Count:", len(drop.get("lessons", [])))
    for it in drop.get("lessons", []):
        print(f"  Title: {it.get('title')}")
        print(f"  Source: {it.get('source_url')}")
        print(f"  Matches Web Developer: {_lesson_matches_career(it, 'Web Developer')}")

asyncio.run(test_fresh())

