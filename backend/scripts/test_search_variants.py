import httpx

for q in ["Travel arrangements", "Corporate travel management", "Business travel"]:
    r = httpx.get(f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json', headers={'User-Agent': 'CareerBeacon/2.0 (mailto:test@careerbeacon.ai)'})
    results = r.json().get('query', {}).get('search', [])
    print(f"\nQuery: '{q}' -> Top 3:")
    for res in results[:3]:
        print(" ", res.get('title'))
