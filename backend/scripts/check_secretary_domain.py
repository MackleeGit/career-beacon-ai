import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_domain():
    cs = ContentService()
    domain = await cs.resolve_career_domain("Secretary and Administrative Assistant", "Managing Calendar Scheduling")
    print("Resolved domain for Secretary:", domain)

asyncio.run(test_domain())
