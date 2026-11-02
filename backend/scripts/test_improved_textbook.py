import os
import sys
import asyncio
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.content_service import ContentService, validate_source_content, strip_html_and_clean
from urllib.parse import quote_plus

async def test_improved_textbook():
    skill_name = "Propulsion System Performance Testing"
    career_title = "Aerospace Engineer"
    headers = {"User-Agent": "CareerBeaconResearch/2.0 (Academic OER Extraction)"}
    async with httpx.AsyncClient(timeout=8.0) as client:
        srch = await client.get(
            f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={quote_plus(skill_name)}&utf8=&format=json&srlimit=5",
            headers=headers
        )
        results = srch.json().get("query", {}).get("search", [])
        print("Search results count:", len(results))
        for item in results:
            title = item.get("title")
            print("Candidate page title:", title)
            ext_resp = await client.get(
                f"https://en.wikibooks.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={quote_plus(title)}&format=json",
                headers=headers
            )
            pages = ext_resp.json().get("query", {}).get("pages", {})
            for _, pdata in pages.items():
                full_extract = strip_html_and_clean(pdata.get("extract", ""))
                tokens = [t.lower() for t in skill_name.split() if len(t) >= 4]
                best_idx = -1
                for tok in tokens:
                    idx = full_extract.lower().find(tok)
                    if idx != -1:
                        best_idx = idx
                        break
                start_idx = max(0, best_idx - 200) if best_idx != -1 else 0
                slice_text = full_extract[start_idx:start_idx + 8000]
                valid = validate_source_content(slice_text, skill_name)
                print(f"  Page '{title}': best_idx={best_idx}, slice_len={len(slice_text)}, valid={valid}")

asyncio.run(test_improved_textbook())

