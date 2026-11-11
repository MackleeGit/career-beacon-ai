import sys
sys.path.insert(0, "backend")
from app.core.database import supabase_client

r = supabase_client.table("careers").select("id, onet_soc_code").execute()
total = len(r.data)
with_soc = len([x for x in r.data if x.get("onet_soc_code")])
print(f"Total careers: {total}, with SOC: {with_soc}")

