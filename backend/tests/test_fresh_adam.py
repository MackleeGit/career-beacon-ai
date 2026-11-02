import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.services.daily_drop_service import DailyDropService, DAILY_SPRINTS_FILE, _load_json_file, _save_json_file, _today_str

async def test_fresh_adam():
    adam_id = "4054e2d2-fa94-4497-8d4f-635610c836d1"
    today = _today_str()
    sprints = _load_json_file(DAILY_SPRINTS_FILE)
    sprints = [s for s in sprints if not (s.get("user_id") == adam_id and s.get("sprint_date") == today)]
    _save_json_file(DAILY_SPRINTS_FILE, sprints)
    print("Cleared existing drop for adamtest.")

    service = DailyDropService()
    drop = await service.get_or_create_daily_drop(adam_id)
    print(f"\nFresh Drop for adamtest:")
    print(f"  Target Focus Skill: {drop.get('target_skill_name')}")
    print(f"  Lessons count: {len(drop.get('lessons', []))}")
    for idx, l in enumerate(drop.get("lessons", []), 1):
        print(f"    {idx}. {l['title']} (Skill: {l.get('skill_name')}, Adapter: {l.get('source_adapter')})")

if __name__ == "__main__":
    asyncio.run(test_fresh_adam())

