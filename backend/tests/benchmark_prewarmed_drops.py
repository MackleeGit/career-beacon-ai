import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.abspath("backend"))

from app.services.daily_drop_service import DailyDropService

TEST_UIDS = [
    ("e955aa77-c9a4-4976-ba6f-a0e6b0edcdf0", "Frontend Developer"),
    ("b2cb517d-8907-4db0-a938-234e799811ff", "Commercial Pilot"),
    ("a4b3c612-0599-4669-b3ac-da946234482a", "ENT Surgeon"),
    ("543d571e-ee87-46db-a330-34a1f77d57f2", "Petroleum Engineer"),
    ("5e63840b-cf51-458a-9985-e86e26d301c7", "Dentists, General"),
    ("8adfd80e-fa24-410b-87fc-5ff3307e425d", "Attorney"),
]

async def benchmark():
    service = DailyDropService()
    print("=" * 70)
    print("BENCHMARK: PRE-WARMED DAILY DROP CLIENT RESPONSE LATENCY")
    print("=" * 70)

    for uid, career in TEST_UIDS:
        t0 = time.time()
        drop = await service.get_or_create_daily_drop(uid)
        dt = (time.time() - t0) * 1000
        lesson_count = len(drop.get("lessons", []))
        focus = drop.get("target_skill_name")
        print(f"User: {career:<22} | Focus: {focus:<32} | Lessons: {lesson_count} | Response: {dt:6.2f}ms")

if __name__ == "__main__":
    asyncio.run(benchmark())

