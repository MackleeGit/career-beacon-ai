import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, source_url").ilike("title", "%Nara Period%").execute()
print("Matches in micro_content:", res.data)
