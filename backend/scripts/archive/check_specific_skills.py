import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

skills_to_check = [
    "Conduct Vulnerability Scanning",
    "Analyze Security Event Logs",
    "Develop Incident Response Playbooks",
]

for name in skills_to_check:
    sk = supabase_client.table("skills").select("id, name").eq("name", name).execute()
    if sk.data:
        sid = sk.data[0]["id"]
        mc = supabase_client.table("micro_content").select("id, title").eq("associated_skill_id", sid).execute()
        print(f"Skill '{name}' (ID: {sid[:8]}...) -> Lessons in micro_content: {len(mc.data or [])}")
    else:
        print(f"Skill '{name}' not found.")

