import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, source_url, associated_skill_id, difficulty_level").eq("associated_skill_id", "13654471-4848-46bf-98fa-e9b4acec93e0").execute()
print(f"Found {len(res.data or [])} lessons for skill 13654471-4848-46bf-98fa-e9b4acec93e0:")
for r in (res.data or []):
    print("ID:", r["id"])
    print("Title:", r["title"].encode("ascii", "replace").decode("ascii"))
    print("URL:", r["source_url"])
    print("Difficulty:", r["difficulty_level"])

