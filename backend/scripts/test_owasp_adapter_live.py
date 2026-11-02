import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_live():
    cs = ContentService()
    print("Testing OWASP adapter for 'Conduct Vulnerability Scanning'...")
    res = await cs.fetch_live_source_for_skill(
        skill_name="Conduct Vulnerability Scanning",
        category="Security Operations",
        career_title="Information Security Analyst",
    )
    if res:
        print("SUCCESS:")
        print("  Title:", res.get("title"))
        print("  Adapter:", res.get("source_adapter"))
        print("  Source:", res.get("source"))
        print("  Trust Score:", res.get("trust_score"))
        print("  URL:", res.get("source_url"))
        print("  Raw Text preview (first 200 chars):", res.get("raw_text")[:200])
    else:
        print("FAILED: No source returned.")

if __name__ == "__main__":
    asyncio.run(test_live())

