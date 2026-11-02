import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

try:
    res = supabase_client.auth.sign_in_with_password({
        "email": "admin@careerbeacon.internal",
        "password": "AdminPassword123!"
    })
    print("SUCCESS: Signed in as admin!")
    print("User ID:", res.user.id)
    print("Access token (first 30 chars):", res.session.access_token[:30], "...")
except Exception as e:
    print("Sign-in failed:", e)

