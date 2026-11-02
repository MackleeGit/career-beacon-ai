import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

res = supabase_client.table("careers").select("id, title").ilike("title", "%develop%").execute()
for r in res.data:
    print(r["title"], r["id"])

res2 = supabase_client.table("careers").select("id, title").ilike("title", "%frontend%").execute()
print("Frontend matches:", len(res2.data))
for r in res2.data:
    print(r["title"], r["id"])

