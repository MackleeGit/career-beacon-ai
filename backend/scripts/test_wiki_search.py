import httpx

r = httpx.get('https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Coordinating+Travel+Arrangements&format=json', headers={'User-Agent': 'CareerBeacon/2.0 (mailto:test@careerbeacon.ai)'})
results = r.json().get('query', {}).get('search', [])
print(f"Results count: {len(results)}")
for res in results[:5]:
    print("Result title:", res.get('title'))
