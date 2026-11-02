import asyncio
import httpx
import re

async def test_owasp():
    headers = {"User-Agent": "CareerBeacon/2.0 (academic research; mailto:research@careerbeacon.ai)"}
    async with httpx.AsyncClient(timeout=8.0) as client:
        # Check listing of cheatsheets from GitHub API
        url = "https://api.github.com/repos/OWASP/CheatSheetSeries/contents/cheatsheets"
        r = await client.get(url, headers=headers)
        print("GitHub OWASP status:", r.status_code)
        if r.status_code == 200:
            files = [item["name"] for item in r.json() if item["name"].endswith(".md")]
            print(f"Total OWASP cheat sheets found: {len(files)}")
            print("Sample cheat sheets:", files[:10])
            
            # Test fetching one
            sample_url = f"https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/{files[0]}"
            r_raw = await client.get(sample_url, headers=headers)
            print("Sample raw fetch status:", r_raw.status_code, "Length:", len(r_raw.text))
            first_lines = "\n".join(r_raw.text.splitlines()[:5])
            print("Preview:\n", first_lines)

if __name__ == "__main__":
    asyncio.run(test_owasp())

