import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def check_adam():
    res = supabase_client.table("profiles").select("*").ilike("email", "%adam%").execute()
    print("Profiles matching 'adam':", len(res.data))
    for p in res.data:
        print(f"ID: {p['id']}, Email: {p.get('email')}, Role: {p.get('role')}, TargetCareer: {p.get('target_career_id')}")
        # check user_skills
        us_res = supabase_client.table("user_skills").select("*, skills(name)").eq("user_id", p["id"]).execute()
        print(f"  User Skills: {len(us_res.data)}")
        for us in us_res.data:
            sk = us.get("skills")
            sname = sk.get("name") if sk else "Unknown"
            print(f"    Skill: {sname} (prof: {us.get('proficiency')})")

    res2 = supabase_client.table("profiles").select("*").ilike("full_name", "%adam%").execute()
    print("Profiles matching full_name 'adam':", len(res2.data))
    for p in res2.data:
        print(f"ID: {p['id']}, FullName: {p.get('full_name')}, Email: {p.get('email')}, TargetCareer: {p.get('target_career_id')}")

if __name__ == "__main__":
    check_adam()
