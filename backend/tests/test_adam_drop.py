import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.services.daily_drop_service import DailyDropService

async def test_adam():
    adam_id = "4054e2d2-fa94-4497-8d4f-635610c836d1"
    service = DailyDropService()
    try:
        drop = await service.get_or_create_daily_drop(adam_id)
        print("Drop successfully generated for adamtest:")
        print(f"  Target Skill: {drop.get('target_skill_name')}")
        print(f"  Lessons count: {len(drop.get('lessons', []))}")
        for l in drop.get("lessons", []):
            print(f"    - {l['title']}")
    except Exception as e:
        print("ERROR for adamtest:", type(e), e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_adam())
