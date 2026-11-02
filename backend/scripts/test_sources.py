import asyncio
import httpx
from urllib.parse import quote_plus

async def test_sources():
    headers = {"User-Agent": "CareerBeacon/2.0 (academic research; mailto:research@careerbeacon.ai)"}
    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Test Aviation
        for q in ["Aeronautical Knowledge", "Aircraft Flight Control System", "Aviation Weather Services"]:
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=2"
            r = await client.get(url, headers=headers)
            print("Aviation search status for", q, ":", r.status_code)
            if r.status_code == 200:
                results = r.json().get("query", {}).get("search", [])
                for res in results:
                    print("  -> Found:", res["title"])

        # 2. Test OSHA / Safety
        for q in ["Occupational safety and health electrical wiring", "Welding safety ventilation", "Fall protection standard"]:
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=2"
            r = await client.get(url, headers=headers)
            print("OSHA search status for", q, ":", r.status_code)
            if r.status_code == 200:
                results = r.json().get("query", {}).get("search", [])
                for res in results:
                    print("  -> Found:", res["title"])

if __name__ == "__main__":
    asyncio.run(test_sources())

