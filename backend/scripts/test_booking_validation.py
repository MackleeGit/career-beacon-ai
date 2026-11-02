import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.mentorship_service import mentorship_service

BASE_URL = "http://127.0.0.1:8000"

async def test_booking_validation():
    store = mentorship_service._ensure_store()
    mentors = store.get("mentors", [])
    if not mentors:
        print("No mentors in store")
        return
    valid_mentor_id = mentors[0]["mentor_id"]
    print(f"Testing against valid mentor: {valid_mentor_id} ({mentors[0]['full_name']})")

    auth_res = supabase_client.auth.sign_in_with_password({
        "email": "admin@careerbeacon.internal",
        "password": "AdminPassword123!"
    })
    token = auth_res.session.access_token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Past date attempt
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        r_past = await client.post(
            f"{BASE_URL}/api/mentor/sessions/book",
            json={"mentor_id": valid_mentor_id, "slot_start_iso": past_time, "topic": "Past test"},
            headers=headers
        )
        print("Past booking response:", r_past.status_code, r_past.text)
        assert r_past.status_code == 400
        assert "past" in r_past.text.lower()

        # 2. Within 24-hr notice attempt
        near_future = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        r_short = await client.post(
            f"{BASE_URL}/api/mentor/sessions/book",
            json={"mentor_id": valid_mentor_id, "slot_start_iso": near_future, "topic": "Short notice test"},
            headers=headers
        )
        print("Short notice booking response:", r_short.status_code, r_short.text)
        assert r_short.status_code == 400
        assert "24 hours" in r_short.text.lower() or "notice" in r_short.text.lower()

        print("SUCCESS: Session booking anti-past and 24-hr advance notice rules verified!")

if __name__ == "__main__":
    asyncio.run(test_booking_validation())

