import httpx

r = httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/Corporate_travel_management', headers={'User-Agent': 'CareerBeacon/2.0 (mailto:test@careerbeacon.ai)'})
print("Status:", r.status_code)
d = r.json()
print("Title:", d.get('title'))
print("Extract:", d.get('extract')[:300])
