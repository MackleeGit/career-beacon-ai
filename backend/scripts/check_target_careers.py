import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

keywords = ["Nurse", "Accountant", "Developer", "Data Scientist", "Mechanical Engineer", "Pilot", "Security Analyst", "Financial", "Electrician", "Paralegal"]

for kw in keywords:
    res = supabase_client.table("careers").select("id, title, onet_soc_code").ilike("title", f"%{kw}%").limit(5).execute()
    titles = [f"{r['title']} ({r['id'][:8]}...)" for r in (res.data or [])]
    print(f"Keyword '{kw}': {titles}")

