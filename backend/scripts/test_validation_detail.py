import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService, validate_source_content

async def check_validation():
    cs = ContentService()
    skill_name = "Propulsion System Performance Testing"
    career_title = "Aerospace Engineer"
    category = "Technical"
    excluded = {'https://en.wikipedia.org/wiki/Occupational_safety_and_health'}
    res = await cs.fetch_live_source_for_skill(skill_name, category, career_title=career_title, exclude_source_urls=excluded)
    if res:
        raw_text = res.get("raw_text", "")
        is_valid = validate_source_content(raw_text, skill_name)
        print("Validation result:", is_valid)
        print("Text length:", len(raw_text))
        print("Contains 'propulsion':", "propulsion" in raw_text.lower())
        print("Contains 'system':", "system" in raw_text.lower())
        print("Contains 'performance':", "performance" in raw_text.lower())
        print("Contains 'testing':", "testing" in raw_text.lower())

asyncio.run(check_validation())

