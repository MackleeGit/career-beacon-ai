import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.daily_drop_service import DailyDropService

async def main():
    service = DailyDropService()
    drop = await service.get_or_create_daily_drop("f216bf54-ec34-451f-b29e-cec85b3e9f50")
    lessons = drop.get("lessons", [])
    print(f"Target Skill: {drop.get('target_skill_name')}")
    print(f"Daily Drop Total Lessons: {len(lessons)}")
    for i, l in enumerate(lessons, 1):
        title = l.get("title", "")
        url = l.get("source_url", "")
        source_type = l.get("source_type", "")
        print(f"{i}. [{source_type}] {title} -> {url}")

if __name__ == "__main__":
    asyncio.run(main())
