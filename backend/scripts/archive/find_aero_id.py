import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("careers").select("id, title").ilike("title", "%Aerospace%").execute()
print("Careers:", res.data)

