import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, source_url, created_at, associated_skill_id").execute()
rows = res.data or []
targets = ["Nara Period", "GABLE", "medical physics", "Japan"]
found = [r for r in rows if any(t.lower() in (r.get("title") or "").lower() for t in targets)]
print(f"Found {len(found)} matching rows in micro_content:")
for f in found:
    print(f)
