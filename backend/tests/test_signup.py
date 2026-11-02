import sys
import os
import time

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def test_signup():
    email = f"elena.rostova.{int(time.time())}@careerbeacon.internal"
    pwd = "TestPassword123!"
    meta = {
        "full_name": "Elena Rostova",
        "first_name": "Elena",
        "last_name": "Rostova",
        "role": "learner",
    }
    print(f"Testing signup for {email}...")
    try:
        res = supabase_client.auth.sign_up({
            "email": email,
            "password": pwd,
            "options": {"data": meta}
        })
        print(f"User created: {res.user.id if res.user else None}")
        print(f"Session available immediately: {bool(res.session)}")
        if res.session:
            print("Auto-confirm is ENABLED! Immediate session returned.")
        else:
            print("Email confirmation required, or no immediate session returned.")
            # Try signing in
            try:
                login_res = supabase_client.auth.sign_in_with_password({"email": email, "password": pwd})
                print("Sign-in succeeded:", bool(login_res.session))
            except Exception as le:
                print("Sign-in notice:", le)
    except Exception as e:
        print("Sign-up exception:", e)

if __name__ == "__main__":
    test_signup()

