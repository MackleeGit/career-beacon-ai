import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_live_source_with_exclusion():
    cs = ContentService()
    skill_name = "Propulsion System Performance Testing"
    career_title = "Aerospace Engineer"
    category = "Technical"
    excluded = {'https://en.wikipedia.org/wiki/Occupational_safety_and_health'}
    print("Calling fetch_live_source_for_skill with exclusion...")
    res = await cs.fetch_live_source_for_skill(skill_name, category, career_title=career_title, exclude_source_urls=excluded)
    if res:
        print("Found source:", res.get("title"), "| URL:", res.get("source_url"), "| Adapter:", res.get("source_adapter"))
    else:
        print("Found source: None")

if __name__ == "__main__":
    asyncio.run(test_live_source_with_exclusion())

