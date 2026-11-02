import asyncio
import httpx
import urllib.parse

async def main():
    headers = {"User-Agent": "CareerMentorBot/1.0 (Educational)"}
    async with httpx.AsyncClient(headers=headers) as client:
        for q in ["Coordinating Travel Arrangements", "Travel Arrangements", "Managing Calendar Scheduling"]:
            r = await client.get(f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json&srlimit=5")
            print(f"Status: {r.status_code}, Length: {len(r.text)}")
            if r.status_code == 200:
                results = r.json().get("query", {}).get("search", [])
                print(f"Query: {q}")
                for item in results:
                    print(" -", item.get("title"))
            else:
                print(r.text[:200])

if __name__ == "__main__":
    asyncio.run(main())
