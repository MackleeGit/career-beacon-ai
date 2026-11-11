import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").select("id, title, associated_skill_id, source_url").eq("associated_skill_id", "13654471-4848-46bf-98fa-e9b4acec93e0").execute()
print("Rows for skill 13654471-4848-46bf-98fa-e9b4acec93e0:", res.data)

res2 = supabase_client.table("micro_content").select("id, title, associated_skill_id, source_url").like("source_url", "%Transportation_Systems_Casebook%").execute()
print("Rows for Transportation_Systems_Casebook:", res2.data)

