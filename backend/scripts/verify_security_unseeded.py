import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

c = supabase_client.table("careers").select("id, title").eq("title", "Information Security Analyst").execute()
cid = c.data[0]["id"]
cs = supabase_client.table("career_skills").select("skill_id, skills(name)").eq("career_id", cid).execute()
sids = [r["skill_id"] for r in cs.data]

mc = supabase_client.table("micro_content").select("id, title, associated_skill_id").in_("associated_skill_id", sids).execute()
print(f"Information Security Analyst essential skills in DB: {len(sids)}")
print(f"Lessons in micro_content for Information Security Analyst: {len(mc.data or [])}")

