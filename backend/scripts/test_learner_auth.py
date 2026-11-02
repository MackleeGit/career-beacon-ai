import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

passwords_to_try = ["Password123!", "AdminPassword123!", "CarlTest123!", "testpassword", "12345678"]
for p in passwords_to_try:
    try:
        res = supabase_client.auth.sign_in_with_password({
            "email": "carltest@gmail.com",
            "password": p
        })
        print(f"SUCCESS with password '{p}': {res.user.id}")
        break
    except Exception as e:
        pass

