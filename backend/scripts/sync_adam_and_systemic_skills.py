import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def sync_skills():
    adam_id = "4054e2d2-fa94-4497-8d4f-635610c836d1"
    career_id = "de6cab44-2961-4694-b46e-b38d724db3e3"
    
    # 1. Fetch all essential skills for Web Developer
    cs_res = supabase_client.table("career_skills").select("skill_id, importance, skills(id, name, category)").eq("career_id", career_id).eq("importance", "essential").execute()
    essential_skills = [row for row in cs_res.data if row.get("skills")]
    print(f"Found {len(essential_skills)} essential skills for Web Developer.")

    # 2. Fetch Adam's current enrolled skills
    us_res = supabase_client.table("user_skills").select("skill_id").eq("user_id", adam_id).execute()
    enrolled_ids = {row["skill_id"] for row in (us_res.data or [])}

    # 3. Insert missing essential skills at baseline proficiency 20%
    to_insert = []
    for es in essential_skills:
        sid = es["skill_id"]
        if sid not in enrolled_ids:
            sname = es["skills"]["name"]
            print(f"  Enrolling missing essential technical skill: '{sname}' ({sid})")
            to_insert.append({
                "user_id": adam_id,
                "skill_id": sid,
                "proficiency": 20,
            })

    if to_insert:
        ins_res = supabase_client.table("user_skills").insert(to_insert).execute()
        print(f"Successfully enrolled {len(ins_res.data)} missing essential skills for adamtest!")
    else:
        print("Adam already has all essential skills enrolled.")

if __name__ == "__main__":
    sync_skills()

