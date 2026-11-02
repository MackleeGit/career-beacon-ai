import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, source_url").ilike("source_url", "%careerbeacon%").execute()
rows = res.data or []
print(f"Found {len(rows)} remaining careerbeacon synthetic rows.")
for r in rows:
    print(f"Deleting {r['id']} - {r['title']} ({r['source_url']})")
    supabase_client.table("micro_content").delete().eq("id", r["id"]).execute()

print("Purge completed successfully.")

