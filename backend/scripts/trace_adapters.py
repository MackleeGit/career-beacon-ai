import os
import sys
import asyncio
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService, validate_source_content

async def trace_adapters():
    cs = ContentService()
    skill_name = "Propulsion System Performance Testing"
    career_title = "Aerospace Engineer"
    category = "Technical"
    excluded = set()

    domain = await cs.resolve_career_domain(career_title, skill_name, category=category)
    print("Resolved domain:", domain)

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        print("\n--- 1. Testing Open Textbook ---")
        try:
            ot = await cs._fetch_open_textbook(client, skill_name, career_title, excluded)
            print("Open Textbook result:", ot.get("title") if ot else None, ot.get("source_url") if ot else None)
        except Exception as e:
            print("Open Textbook err:", e)

        print("\n--- 2. Testing Clinical Science ---")
        try:
            cs_res = await cs._fetch_clinical_and_science(client, skill_name, career_title, excluded)
            print("Clinical Science result:", cs_res.get("title") if cs_res else None)
        except Exception as e:
            print("Clinical Science err:", e)

        print("\n--- 3. Testing OSHA ---")
        try:
            osha_res = await cs._fetch_osha_standards(client, skill_name, career_title, excluded)
            print("OSHA result:", osha_res.get("title") if osha_res else None)
        except Exception as e:
            print("OSHA err:", e)

        print("\n--- 4. Testing YouTube ---")
        try:
            yt_res = await cs._fetch_youtube_lecture(client, skill_name, career_title, excluded)
            print("YouTube result:", yt_res.get("title") if yt_res else None)
        except Exception as e:
            print("YouTube err:", e)

        print("\n--- 5. Testing OpenAlex ---")
        try:
            oa_res = await cs._fetch_openalex_chapter(client, skill_name, career_title, excluded)
            print("OpenAlex result:", oa_res.get("title") if oa_res else None)
        except Exception as e:
            print("OpenAlex err:", e)

        print("\n--- 6. Testing Wikipedia Fallback ---")
        try:
            wiki_res = await cs._fetch_wikipedia_fallback(client, skill_name, excluded)
            print("Wikipedia result:", wiki_res.get("title") if wiki_res else None)
        except Exception as e:
            print("Wikipedia err:", e)

if __name__ == "__main__":
    asyncio.run(trace_adapters())

