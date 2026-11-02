import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_live_source():
    cs = ContentService()
    skill_name = "Propulsion System Performance Testing"
    career_title = "Aerospace Engineer"
    category = "Technical"
    print("Calling fetch_live_source_for_skill...")
    res = await cs.fetch_live_source_for_skill(skill_name, category, career_title=career_title)
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(test_live_source())

