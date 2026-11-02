import sys
sys.path.insert(0, "backend")

from app.core.database import supabase_client

res = supabase_client.table("profiles").select("id, full_name, role, target_career_id").execute()
print(f"Total profiles: {len(res.data)}")
for p in res.data:
    cid = p.get("target_career_id")
    c_title = ""
    if cid:
        c_res = supabase_client.table("careers").select("title").eq("id", cid).execute()
        if c_res.data:
            c_title = c_res.data[0].get("title", "")
    print(f"- {p['id']} | {p.get('full_name')} | role: {p.get('role')} | career: {c_title}")
