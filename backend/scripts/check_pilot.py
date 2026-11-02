import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("careers").select("id, title").ilike("title", "%Pilot%").execute()
for c in res.data:
    cid = c["id"]
    all_cs = supabase_client.table("career_skills").select("importance, tier, skills(name)").eq("career_id", cid).limit(10).execute()
    print(f"Career: {c['title']} ({cid})")
    for r in (all_cs.data or [])[:5]:
        print(f"  - skill: {r.get('skills', {}).get('name')}, importance: {r.get('importance')}, tier: {r.get('tier')}")
