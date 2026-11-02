import os
import sys
import asyncio
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_dynamic_lesson():
    cs = ContentService()
    try:
        print("Calling generate_dynamic_lesson_for_skill...")
        res = await cs.generate_dynamic_lesson_for_skill(
            skill_id="13654471-4848-46bf-98fa-e9b4acec93e0",
            skill_name="Propulsion System Performance Testing",
            category="Technical",
            career_title="Aerospace Engineer",
            target_proficiency=20
        )
        print("Result:", res)
    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_dynamic_lesson())

