import os
import sys
import asyncio
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService

async def test_secretary_sources():
    cs = ContentService()
    # Add business_admin to domain anchors in runtime for test
    for skill in ["Coordinating Travel Arrangements", "Managing Calendar Scheduling"]:
        print(f"\n--- Testing source for: {skill} ---")
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            excluded = set()
            # Try structured_tutorial
            st = await cs._fetch_structured_tutorial(client, skill, "Administrative", excluded)
            print("Structured Tutorial:", st.get("title") if st else None, st.get("source_url") if st else None)

            # Try YouTube
            yt = await cs._fetch_youtube_lecture(client, skill, "Secretary and Administrative Assistant", excluded)
            print("YouTube:", yt.get("title") if yt else None, yt.get("source_url") if yt else None)

            # Try OpenAlex
            oa = await cs._fetch_openalex_chapter(client, skill, "Secretary and Administrative Assistant", excluded)
            print("OpenAlex:", oa.get("title") if oa else None, oa.get("source_url") if oa else None)

            # Try Wikipedia fallback
            wiki = await cs._fetch_wikipedia_fallback(client, skill, excluded)
            print("Wikipedia:", wiki.get("title") if wiki else None, wiki.get("source_url") if wiki else None)

asyncio.run(test_secretary_sources())
