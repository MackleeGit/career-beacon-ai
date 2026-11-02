import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, associated_skill_id, source_url").execute()
rows = res.data or []
print(f"Total rows in micro_content: {len(rows)}")
for r in rows[:15]:
    print(r)

