import sys
import os
import json
import uuid
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

async def main():
    print("=" * 70)
    print("PREPARING PRISTINE TWO-ACCOUNT DEMO BASELINE")
    print("=" * 70)

    emb = EmbeddingService()

    # 1. Careers
    careers_res = supabase_client.table("careers").select("id, title, onet_soc_code").execute()
    careers_by_title = {c["title"].lower(): c for c in (careers_res.data or [])}

    softdev_career = next((c for t, c in careers_by_title.items() if "software developer" in t), None)
    if not softdev_career:
        softdev_career = next((c for t, c in careers_by_title.items() if "web developer" in t), None)
    ent_career = next((c for t, c in careers_by_title.items() if "ent surgeon" in t or "otolaryngol" in t), None)
    if not ent_career:
        ent_career = next((c for t, c in careers_by_title.items() if "surgeon" in t), None)

    print(f"Software Dev Career: {softdev_career['title']} ({softdev_career['id']})")
    print(f"ENT Surgeon Career: {ent_career['title']} ({ent_career['id']})")

    # 2. Existing Learner: softdev.learner@demo.com
    learner_email = "softdev.learner@demo.com"
    learner_pwd = "DemoPassword123!"

    auth_users = supabase_client.auth.admin.list_users()
    learner_user = next((u for u in auth_users if u.email == learner_email), None)

    if not learner_user:
        print(f"Creating Baseline Learner: {learner_email}")
        res = supabase_client.auth.admin.create_user({
            "email": learner_email,
            "password": learner_pwd,
            "email_confirm": True,
            "user_metadata": {
                "full_name": "Jordan Blake",
                "role": "learner",
                "target_career_id": softdev_career["id"],
                "target_career_title": softdev_career["title"],
            }
        })
        learner_id = res.user.id
    else:
        learner_id = learner_user.id
    print(f"Baseline Learner ID: {learner_id}")

    # Upsert profiles table
    supabase_client.table("profiles").upsert({
        "id": learner_id,
        "email": learner_email,
        "full_name": "Jordan Blake",
        "role": "learner",
        "target_career_id": softdev_career["id"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Enroll essential software dev skills
    cs_skills = supabase_client.table("career_skills").select("skill_id").eq("career_id", softdev_career["id"]).limit(5).execute()
    user_skills_entries = []
    for row in (cs_skills.data or []):
        user_skills_entries.append({
            "user_id": learner_id,
            "skill_id": row["skill_id"],
            "proficiency": 35,
        })
    if user_skills_entries:
        supabase_client.table("user_skills").upsert(user_skills_entries).execute()
        print(f"Enrolled {len(user_skills_entries)} baseline skills for learner Jordan Blake")

    # 3. Existing Mentor: ent.mentor@demo.com
    mentor_email = "ent.mentor@demo.com"
    mentor_pwd = "DemoPassword123!"

    mentor_user = next((u for u in auth_users if u.email == mentor_email), None)
    if not mentor_user:
        print(f"Creating Baseline Mentor: {mentor_email}")
        res = supabase_client.auth.admin.create_user({
            "email": mentor_email,
            "password": mentor_pwd,
            "email_confirm": True,
            "user_metadata": {
                "full_name": "Dr. Evelyn Harper",
                "role": "mentor",
                "headline": "Board Certified Otolaryngologist & Head/Neck Surgeon",
                "bio": "Over 12 years of surgical clinical practice specializing in microsurgical reconstruction, endoscopic sinus surgery, and head & neck oncology. Passionate about training the next generation of surgeons.",
            }
        })
        mentor_id = res.user.id
    else:
        mentor_id = mentor_user.id
    print(f"Baseline Mentor ID: {mentor_id}")

    # Upsert profiles table
    supabase_client.table("profiles").upsert({
        "id": mentor_id,
        "email": mentor_email,
        "full_name": "Dr. Evelyn Harper",
        "role": "mentor",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Upsert mentors table in Supabase
    supabase_client.table("mentors").upsert({
        "id": mentor_id,
        "profile_id": mentor_id,
        "bio": "Over 12 years of surgical clinical practice specializing in microsurgical reconstruction, endoscopic sinus surgery, and head & neck oncology.",
        "expertise": f"{ent_career['title']} | Otolaryngologist | Microsurgical techniques, Head and neck anatomy, Endoscopic surgical procedures, Pediatric airway management",
        "rating_avg": 5.0,
        "rating_count": 14,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Upsert in mentorship_ecosystem.json
    eco_path = "backend/data/mentorship_ecosystem.json"
    eco = {"mentors": [], "connections": [], "messages": [], "pulse_posts": [], "questions": [], "sessions": []}
    if os.path.exists(eco_path):
        try:
            with open(eco_path, "r", encoding="utf-8") as f:
                eco = json.load(f)
        except Exception:
            pass

    mentor_vec = await emb.get_embedding(f"ENT Surgeon Otolaryngologist Microsurgical techniques Head and neck anatomy Endoscopic surgical procedures Pediatric airway management")

    # Update or add mentor in eco
    eco["mentors"] = [m for m in eco.get("mentors", []) if m.get("mentor_id") != mentor_id]
    eco["mentors"].append({
        "mentor_id": mentor_id,
        "full_name": "Dr. Evelyn Harper",
        "primary_domain": "ENT Surgeon",
        "headline": "Board Certified Otolaryngologist & Head/Neck Surgeon",
        "bio": "Over 12 years of surgical clinical practice specializing in microsurgical reconstruction, endoscopic sinus surgery, and head & neck oncology.",
        "expertise_skills": ["Microsurgical techniques", "Head and neck anatomy", "Endoscopic surgical procedures", "Pediatric airway management"],
        "weekly_hours": 6,
        "available_days": ["Mon", "Wed", "Fri"],
        "preferred_time_window": "Afternoon",
        "max_mentees": 4,
        "active_mentees_count": 0,
        "verified_sessions_count": 14,
        "avg_rating": 5.0,
        "is_seeded": True,
        "mentor_vector": mentor_vec,
    })

    with open(eco_path, "w", encoding="utf-8") as f:
        json.dump(eco, f, indent=2)
    print("Registered Dr. Evelyn Harper in mentorship_ecosystem.json with availability and embedding vector")

    # 4. Clean up accounts that will be created live during the demo
    demo_created_emails = [
        "ent.learner@demo.com",
        "softdev.mentor@demo.com",
        "new.ent.learner@demo.com",
        "new.softdev.mentor@demo.com",
        "demo.ent.learner@gmail.com",
        "demo.softdev.mentor@gmail.com",
    ]
    for u in auth_users:
        if u.email in demo_created_emails:
            print(f"Purged previous test demo account: {u.email} ({u.id})")
            supabase_client.auth.admin.delete_user(u.id)

    print("\n" + "=" * 70)
    print("DEMO BASELINE SETUP COMPLETE:")
    print(f"1. Existing Learner: {learner_email} / {learner_pwd}")
    print(f"   Career: {softdev_career['title']} | Role: learner")
    print(f"2. Existing Mentor:  {mentor_email} / {mentor_pwd}")
    print(f"   Domain: {ent_career['title']} | Role: mentor")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
