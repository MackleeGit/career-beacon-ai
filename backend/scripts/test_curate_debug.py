import os
import sys
import asyncio
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.daily_drop_service import DailyDropService

async def test_curate():
    service = DailyDropService()
    user_id = "9c4d483e-1296-4c24-8a78-fb09b2e30181"
    try:
        drop = await service._curate_daily_drop(user_id=user_id, sprint_date="2026-11-02", priority_index=0)
        print("Curate result:", drop)
    except Exception as e:
        print("Error during curate:", e)
        traceback.print_exc()

asyncio.run(test_curate())

