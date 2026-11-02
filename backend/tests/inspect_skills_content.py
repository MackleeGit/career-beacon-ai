import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def inspect():
    res = supabase_client.table("micro_content").select("id, title, associated_skill_id").execute()
    rows = res.data or []
    skill_ids = set(r["associated_skill_id"] for r in rows if r.get("associated_skill_id"))
    print(f"Total rows: {len(rows)}, Distinct associated_skill_ids: {len(skill_ids)}")
    for sid in list(skill_ids)[:15]:
        s = supabase_client.table("skills").select("name, category").eq("id", sid).execute()
        sname = s.data[0]["name"] if s.data else "Unknown"
        scat = s.data[0]["category"] if s.data else "Unknown"
        cnt = sum(1 for r in rows if r.get("associated_skill_id") == sid)
        print(f"  Skill: '{sname}' ({scat}): {cnt} lessons")

if __name__ == "__main__":
    inspect()

