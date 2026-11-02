import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def backfill_all_legacy_accounts():
    print("=" * 80)
    print("BACKFILLING ESSENTIAL CAREER SKILLS FOR ALL PROFILES")
    print("=" * 80)

    # 1. Fetch all profiles with a target career
    prof_res = supabase_client.table("profiles").select("id, email, full_name, role, target_career_id").not_.is_("target_career_id", "null").execute()
    profiles = prof_res.data or []
    print(f"Found {len(profiles)} profiles with assigned target careers.")

    total_backfilled_skills = 0
    accounts_updated = 0

    for prof in profiles:
        uid = prof["id"]
        career_id = prof["target_career_id"]
        email = prof.get("email") or "No email"

        # Fetch career title
        c_res = supabase_client.table("careers").select("title").eq("id", career_id).execute()
        career_title = c_res.data[0]["title"] if c_res.data else "Unknown"

        # Fetch essential skills for this career
        cs_res = supabase_client.table("career_skills").select(
            "skill_id, importance, skills(id, name, category)"
        ).eq("career_id", career_id).eq("importance", "essential").execute()

        essential_skills = [row for row in (cs_res.data or []) if row.get("skills")]
        if not essential_skills:
            continue

        # Fetch user's currently enrolled skills
        us_res = supabase_client.table("user_skills").select("skill_id").eq("user_id", uid).execute()
        enrolled_ids = {row["skill_id"] for row in (us_res.data or [])}

        missing_skills = [es for es in essential_skills if es["skill_id"] not in enrolled_ids]
        if missing_skills:
            print(f"\nUser: {email} ({uid[:8]}...) | Career: {career_title}")
            print(f"  Enrolled: {len(enrolled_ids)} | Missing Essential Skills: {len(missing_skills)}")

            to_insert = [
                {
                    "user_id": uid,
                    "skill_id": ms["skill_id"],
                    "proficiency": 20,
                }
                for ms in missing_skills
            ]

            ins_res = supabase_client.table("user_skills").insert(to_insert).execute()
            inserted_count = len(ins_res.data or [])
            total_backfilled_skills += inserted_count
            accounts_updated += 1
            for ms in missing_skills[:5]:
                print(f"    + Enrolled: {ms['skills']['name']} ({ms['skills'].get('category')})")
            if len(missing_skills) > 5:
                print(f"    ... and {len(missing_skills) - 5} more.")

    print("\n" + "=" * 80)
    print(f"BACKFILL COMPLETE:")
    print(f"  Profiles Scanned: {len(profiles)}")
    print(f"  Accounts Updated: {accounts_updated}")
    print(f"  Total Essential Skills Backfilled: {total_backfilled_skills}")
    print("=" * 80)

if __name__ == "__main__":
    backfill_all_legacy_accounts()

