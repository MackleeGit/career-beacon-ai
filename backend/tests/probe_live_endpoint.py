import httpx

r = httpx.get("http://localhost:8000/api/recommendations/daily-drop/current")
print("Status code:", r.status_code)
print("Response text:", r.text)
