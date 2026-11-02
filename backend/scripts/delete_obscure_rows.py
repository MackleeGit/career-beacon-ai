import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").delete().ilike("title", "%Emergent Complexity%").execute()
print("Deleted Emergent Complexity rows.")
res2 = supabase_client.table("micro_content").delete().ilike("title", "%Guide to Unix%").execute()
print("Deleted Guide to Unix rows for Secretary.")
