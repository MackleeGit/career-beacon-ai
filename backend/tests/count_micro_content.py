import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def inspect_micro_content():
    count_res = supabase_client.table("micro_content").select("id", count="exact").execute()
    print(f"Total micro_content rows in database: {count_res.count}")
    
    # Check distinct careers
    res = supabase_client.table("micro_content").select("career_id").execute()
    career_ids = set(r["career_id"] for r in (res.data or []) if r.get("career_id"))
    print(f"Distinct career_ids with micro_content: {len(career_ids)}")
    for cid in list(career_ids)[:10]:
        c = supabase_client.table("careers").select("title").eq("id", cid).execute()
        title = c.data[0]["title"] if c.data else "Unknown"
        cnt = sum(1 for r in res.data if r.get("career_id") == cid)
        print(f"  {title} ({cid}): {cnt} lessons")

if __name__ == "__main__":
    inspect_micro_content()

