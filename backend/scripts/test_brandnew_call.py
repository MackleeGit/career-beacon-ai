import os
import sys
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

# Sign in as brandnew.d291acc8@careerbeacon.internal
auth_res = supabase_client.auth.sign_in_with_password({
    "email": "brandnew.d291acc8@careerbeacon.internal",
    "password": "TestPassword123!"
})
token = auth_res.session.access_token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with httpx.Client(timeout=30.0) as client:
    r = client.get("http://127.0.0.1:8000/api/recommendations/daily-drop/current", headers=headers)
    print("Status:", r.status_code)
    resp = r.json()
    drop = resp.get("drop", {})
    print("Lessons count:", len(drop.get("lessons", [])))
    print("Target skill:", drop.get("target_skill_name"))
    print("Is completed:", drop.get("is_completed"))
    for l in drop.get("lessons", []):
        print("  Lesson:", l.get("title"))

