import os
import sys
import uuid
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

BASE_URL = "http://127.0.0.1:8000"

def test_new_user_drop():
    email = f"brandnew.{uuid.uuid4().hex[:8]}@careerbeacon.internal"
    password = "TestPassword123!"

    print(f"1. Registering new user: {email}")
    reg_res = supabase_client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": "Test Brand New User", "role": "learner"}}
    })
    user_id = reg_res.user.id
    token = reg_res.session.access_token
    print(f"User ID: {user_id}")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 2. Check before career set
    print("\n2. Calling /api/recommendations/daily-drop/current BEFORE onboarding...")
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BASE_URL}/api/recommendations/daily-drop/current", headers=headers)
        print("Status:", r.status_code)
        resp_json = r.json()
        drop = resp_json.get("drop", {})
        print("Drop before career: lessons count:", len(drop.get("lessons", [])))

    # 3. Now set career to Aerospace Engineer
    print("\n3. Setting user profile target_career_id to Aerospace Engineer...")
    supabase_client.table("profiles").update({"target_career_id": "5b833969-a934-437d-85c5-fa078b105aa4"}).eq("id", user_id).execute()

    # 4. Call daily-drop/current AFTER career set
    print("\n4. Calling /api/recommendations/daily-drop/current AFTER career set...")
    with httpx.Client(timeout=30.0) as client:
        r2 = client.get(f"{BASE_URL}/api/recommendations/daily-drop/current", headers=headers)
        print("Status:", r2.status_code)
        resp2 = r2.json()
        drop2 = resp2.get("drop", {})
        print("Drop after career: lessons count:", len(drop2.get("lessons", [])))
        print("Target skill:", drop2.get("target_skill_name"))
        print("Is completed:", drop2.get("is_completed"))

if __name__ == "__main__":
    test_new_user_drop()
