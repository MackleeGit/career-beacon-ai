import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("profiles").select("id, email, target_career_id").eq("id", "9c4d483e-1296-4c24-8a78-fb09b2e30181").execute()
print("Profile data for 9c4d483e-1296-4c24-8a78-fb09b2e30181:", res.data)

