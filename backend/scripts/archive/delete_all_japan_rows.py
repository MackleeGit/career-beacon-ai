import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("micro_content").delete().ilike("title", "%History of Japan%").execute()
print("Deleted History of Japan rows from micro_content.")
res2 = supabase_client.table("micro_content").delete().ilike("source_url", "%History_of_Japan%").execute()
print("Deleted History of Japan URLs from micro_content.")
