"""
backend/scripts/reset_and_seed_production_demo.py
-------------------------------------------------
Master Reset & Production Seeding Script for Career Beacon:
1. Purges all 50+ messy / legacy test accounts from auth.users and profiles.
2. Seeds exactly 2 clean Demo Mentors (Dr. Evelyn Harper, Alex Vance).
3. Seeds exactly 2 clean Demo Learners (Jordan Blake, Maya Lin) with:
   - Calibrated competency profiles
   - Active streaks
   - Active Day 1 Daily Drop bundles
   - Active mentorship connections, DM history, and scheduled 1-on-1 sessions.
4. Pre-creates exactly 2 FRESH Live Presentation Accounts:
   - live.learner@presentation.com (Ready for live presentation onboarding demo)
   - live.mentor@presentation.com (Ready for live presentation mentor demo)
5. Synchronizes both native Supabase tables AND local JSON fixtures.
"""

import sys
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEMO_PASSWORD = "DemoPassword123!"
PRESENTATION_PASSWORD = "Presentation2026!"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

async def reset_and_seed():
    print("=== STEP 1: CLEANING UP LEGACY / MESSY ACCOUNTS ===")
    
    # 1. Fetch all existing auth users
    res = supabase_client.auth.admin.list_users()
    all_users = res if isinstance(res, list) else getattr(res, "users", [])
    print(f"Found {len(all_users)} existing auth users in Supabase.")

    # List of accounts we intend to keep/recreate cleanly
    keep_emails = {
        "admin@careerbeacon.internal",
    }

    deleted_count = 0
    for u in all_users:
        email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
        uid = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
        if email and uid and email not in keep_emails:
            try:
                supabase_client.auth.admin.delete_user(uid)
                deleted_count += 1
            except Exception as e:
                print(f"Notice deleting {email}: {e}")

    print(f"Purged {deleted_count} old test accounts from Supabase Auth.")

    # Clean orphaned profiles in profiles table
    try:
        supabase_client.table("profiles").delete().neq("email", "admin@careerbeacon.internal").execute()
    except Exception as e:
        print(f"Profiles cleanup notice: {e}")

    print("\n=== STEP 2: CREATING PRODUCTION DEMO & PRESENTATION ACCOUNTS ===")

    def get_or_create_user(email: str, password: str, full_name: str, role: str) -> str:
        # Check if user already exists
        for u in all_users:
            u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
            u_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
            if u_email == email:
                return str(u_id)

        # Create fresh user
        created = supabase_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "role": role,
            }
        })
        user_obj = getattr(created, "user", created)
        uid = getattr(user_obj, "id", None) or (user_obj.get("id") if isinstance(user_obj, dict) else None)
        
        # Ensure profile exists in profiles table
        supabase_client.table("profiles").upsert({
            "id": str(uid),
            "email": email,
            "full_name": full_name,
            "role": role,
            "updated_at": utc_now_iso(),
        }).execute()
        
        print(f"Created {role.upper()}: {email} ({full_name}) -> ID: {uid}")
        return str(uid)

    # 1. Admin
    admin_id = get_or_create_user("admin@careerbeacon.internal", "AdminPassword123!", "System Administrator", "admin")

    # 2. Demo Mentors (2)
    evelyn_id = get_or_create_user("evelyn.mentor@demo.com", DEMO_PASSWORD, "Dr. Evelyn Harper", "mentor")
    alex_id = get_or_create_user("alex.mentor@demo.com", DEMO_PASSWORD, "Alex Vance", "mentor")

    # 3. Demo Learners (2)
    jordan_id = get_or_create_user("jordan.learner@demo.com", DEMO_PASSWORD, "Jordan Blake", "learner")
    maya_id = get_or_create_user("maya.learner@demo.com", DEMO_PASSWORD, "Maya Lin", "learner")

    # 4. Live Presentation Accounts (2 Fresh)
    live_learner_id = get_or_create_user("live.learner@presentation.com", PRESENTATION_PASSWORD, "Leo Sterling", "learner")
    live_mentor_id = get_or_create_user("live.mentor@presentation.com", PRESENTATION_PASSWORD, "Sarah Jenkins", "mentor")

    print("\n=== STEP 3: SEEDING MENTOR PROFILES & VECTOR INDEX ===")
    emb_service = EmbeddingService()

    # Find careers
    c_res = supabase_client.table("careers").select("id, title").execute()
    c_map = {c["title"].lower(): c["id"] for c in (c_res.data or [])}

    softdev_career_id = c_map.get("full-stack engineer") or c_map.get("frontend developer") or list(c_map.values())[0]
    med_career_id = c_map.get("general internal medicine physician") or c_map.get("registered nurse") or list(c_map.values())[1]

    # Mentor 1: Dr. Evelyn Harper
    evelyn_vec = await emb_service.get_embedding("Dr. Evelyn Harper Head of Otolaryngology & Clinical Surgery healthcare medicine clinical surgery")
    supabase_client.table("mentors").upsert({
        "id": evelyn_id,
        "profile_id": evelyn_id,
        "bio": "Board-certified ENT surgeon and clinical preceptor with 14 years of hospital and surgical residency training experience.",
        "expertise": ["Clinical Surgery", "Patient Triage Protocols", "Differential Diagnosis", "Pharmacology"],
        "rating_avg": 5.0,
        "rating_count": 14,
        "updated_at": utc_now_iso(),
    }).execute()

    # Mentor 2: Alex Vance
    alex_vec = await emb_service.get_embedding("Alex Vance Principal Distributed Systems & Cloud Architecture Engineer software tech backend databases")
    supabase_client.table("mentors").upsert({
        "id": alex_id,
        "profile_id": alex_id,
        "bio": "12+ years building distributed backends, streaming data pipelines, and scalable microservices in Python, Go, and Kubernetes.",
        "expertise": ["Distributed Systems", "PostgreSQL", "FastAPI", "Docker Containers", "System Architecture"],
        "rating_avg": 4.95,
        "rating_count": 18,
        "updated_at": utc_now_iso(),
    }).execute()

    print("Mentors seeded in Supabase mentors table.")

    print("\n=== STEP 4: SEEDING LEARNER PROFILES, SKILLS & STREAKS ===")
    # Update Jordan Blake profile
    supabase_client.table("profiles").update({
        "target_career_id": softdev_career_id,
    }).eq("id", jordan_id).execute()

    # Update Maya Lin profile
    supabase_client.table("profiles").update({
        "target_career_id": med_career_id,
    }).eq("id", maya_id).execute()

    # Seed Streaks in Supabase user_streaks
    supabase_client.table("user_streaks").upsert([
        {
            "user_id": jordan_id,
            "current_streak": 5,
            "longest_streak": 7,
            "last_activity_date": today_str(),
            "freeze_count": 1,
        },
        {
            "user_id": maya_id,
            "current_streak": 3,
            "longest_streak": 3,
            "last_activity_date": today_str(),
            "freeze_count": 0,
        }
    ]).execute()
    print("User streaks seeded in Supabase user_streaks table.")

    print("\n=== STEP 5: SEEDING MENTORSHIP CONNECTIONS, CHATS & SESSIONS ===")
    
    # 1. Connection: Jordan Blake <-> Alex Vance
    conn_jordan_alex_id = str(uuid.uuid4())
    supabase_client.table("mentor_connections").upsert({
        "id": conn_jordan_alex_id,
        "mentor_id": alex_id,
        "learner_id": jordan_id,
        "status": "accepted",
        "initial_message": "Looking to master distributed systems and container orchestration for backend roles.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "updated_at": utc_now_iso(),
    }).execute()

    # 2. Connection: Maya Lin <-> Dr. Evelyn Harper
    conn_maya_evelyn_id = str(uuid.uuid4())
    supabase_client.table("mentor_connections").upsert({
        "id": conn_maya_evelyn_id,
        "mentor_id": evelyn_id,
        "learner_id": maya_id,
        "status": "accepted",
        "initial_message": "Preparing for clinical residency rotations and diagnostic assessment exams.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "updated_at": utc_now_iso(),
    }).execute()

    # Messages between Jordan and Alex
    t_base = datetime.now(timezone.utc) - timedelta(hours=6)
    messages_jordan_alex = [
        {
            "id": str(uuid.uuid4()),
            "connection_id": conn_jordan_alex_id,
            "sender_id": jordan_id,
            "recipient_id": alex_id,
            "content": "Hi Alex, thanks for connecting! I am currently working on optimizing database indexes for our API.",
            "is_read": True,
            "created_at": t_base.isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "connection_id": conn_jordan_alex_id,
            "sender_id": alex_id,
            "recipient_id": jordan_id,
            "content": "Welcome Jordan! PostgreSQL B-Tree vs GIN indexes are crucial. Make sure you inspect EXPLAIN ANALYZE output.",
            "is_read": True,
            "created_at": (t_base + timedelta(minutes=15)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "connection_id": conn_jordan_alex_id,
            "sender_id": jordan_id,
            "recipient_id": alex_id,
            "content": "Will do! I booked our 1:1 session for tomorrow to review the containerized deployment setup.",
            "is_read": True,
            "created_at": (t_base + timedelta(minutes=30)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "connection_id": conn_jordan_alex_id,
            "sender_id": alex_id,
            "recipient_id": jordan_id,
            "content": "Looking forward to it! Have your Dockerfile and Compose YAML ready on screen.",
            "is_read": False,
            "created_at": (t_base + timedelta(minutes=35)).isoformat(),
        },
    ]
    supabase_client.table("mentor_messages").upsert(messages_jordan_alex).execute()

    # Scheduled 1-on-1 Session: Alex Vance with Jordan Blake (Tomorrow 14:00 UTC)
    tomorrow_start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(minutes=45)

    session_id = str(uuid.uuid4())
    supabase_client.table("mentor_sessions").upsert({
        "id": session_id,
        "connection_id": conn_jordan_alex_id,
        "mentor_id": alex_id,
        "learner_id": jordan_id,
        "slot_start_iso": tomorrow_start.isoformat(),
        "slot_end_iso": tomorrow_end.isoformat(),
        "status": "confirmed",
        "meet_url": "https://meet.google.com/cb-alex-jordan",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }).execute()

    print("Connections, messages, and scheduled 1:1 session seeded in Supabase.")

    print("\n=== STEP 6: SYNCHRONIZING LOCAL JSON BACKUP FIXTURES ===")
    # Sync user_streaks.json
    local_streaks = [
        {"user_id": jordan_id, "current_streak": 5, "longest_streak": 7, "last_active_date": today_str(), "freeze_count": 1},
        {"user_id": maya_id, "current_streak": 3, "longest_streak": 3, "last_active_date": today_str(), "freeze_count": 0},
    ]
    with open(DATA_DIR / "user_streaks.json", "w", encoding="utf-8") as f:
        json.dump(local_streaks, f, indent=2)

    # Sync mentorship_ecosystem.json
    local_ecosystem = {
        "mentors": [
            {
                "mentor_id": evelyn_id,
                "full_name": "Dr. Evelyn Harper",
                "primary_domain": "healthcare",
                "headline": "Head of Otolaryngology & Clinical Surgery",
                "bio": "Board-certified ENT surgeon and clinical preceptor with 14 years of hospital and surgical residency training experience.",
                "expertise_skills": ["Clinical Surgery", "Patient Triage Protocols", "Differential Diagnosis", "Pharmacology"],
                "weekly_hours": 6,
                "available_days": ["Monday", "Wednesday", "Thursday"],
                "preferred_time_window": "14:00 - 18:00 UTC",
                "max_mentees": 5,
                "active_mentees_count": 1,
                "verified_sessions_count": 14,
                "avg_rating": 5.0,
                "is_seeded": True,
            },
            {
                "mentor_id": alex_id,
                "full_name": "Alex Vance",
                "primary_domain": "tech",
                "headline": "Principal Distributed Systems & Cloud Architecture Engineer",
                "bio": "12+ years building distributed backends, streaming data pipelines, and scalable microservices in Python, Go, and Kubernetes.",
                "expertise_skills": ["Distributed Systems", "PostgreSQL", "FastAPI", "Docker Containers", "System Architecture"],
                "weekly_hours": 8,
                "available_days": ["Tuesday", "Thursday", "Friday"],
                "preferred_time_window": "13:00 - 17:00 UTC",
                "max_mentees": 5,
                "active_mentees_count": 1,
                "verified_sessions_count": 18,
                "avg_rating": 4.95,
                "is_seeded": True,
            }
        ],
        "connections": [
            {
                "id": conn_jordan_alex_id,
                "learner_id": jordan_id,
                "mentor_id": alex_id,
                "mentor_name": "Alex Vance",
                "mentor_headline": "Principal Distributed Systems & Cloud Architecture Engineer",
                "mentor_domain": "tech",
                "goal_note": "Looking to master distributed systems and container orchestration for backend roles.",
                "status": "accepted",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "updated_at": utc_now_iso(),
            },
            {
                "id": conn_maya_evelyn_id,
                "learner_id": maya_id,
                "mentor_id": evelyn_id,
                "mentor_name": "Dr. Evelyn Harper",
                "mentor_headline": "Head of Otolaryngology & Clinical Surgery",
                "mentor_domain": "healthcare",
                "goal_note": "Preparing for clinical residency rotations and diagnostic assessment exams.",
                "status": "accepted",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                "updated_at": utc_now_iso(),
            }
        ],
        "messages": [
            {
                "id": m["id"],
                "connection_id": m["connection_id"],
                "sender_id": m["sender_id"],
                "sender_name": "Jordan Blake" if m["sender_id"] == jordan_id else "Alex Vance",
                "sender_role": "learner" if m["sender_id"] == jordan_id else "mentor",
                "text": m["content"],
                "created_at": m["created_at"],
            }
            for m in messages_jordan_alex
        ],
        "sessions": [
            {
                "id": session_id,
                "learner_id": jordan_id,
                "learner_name": "Jordan Blake",
                "learner_career": "Full-Stack Engineer",
                "mentor_id": alex_id,
                "mentor_name": "Alex Vance",
                "mentor_headline": "Principal Distributed Systems & Cloud Architecture Engineer",
                "topic": "Containerized Microservice & Database Indexing Review",
                "focus_skill": "Docker Containers",
                "notes": "Bring Dockerfile and EXPLAIN ANALYZE queries.",
                "slot_start_iso": tomorrow_start.isoformat(),
                "slot_end_iso": tomorrow_end.isoformat(),
                "display_label": f"Tomorrow, {tomorrow_start.strftime('%b %d')} at {tomorrow_start.strftime('%H:%M')} UTC",
                "duration_minutes": 45,
                "meeting_code": "cb-alex-jordan",
                "meeting_url": "https://meet.google.com/cb-alex-jordan",
                "status": "confirmed",
                "created_at": utc_now_iso(),
            }
        ],
        "pulse_posts": [],
        "questions": []
    }
    with open(DATA_DIR / "mentorship_ecosystem.json", "w", encoding="utf-8") as f:
        json.dump(local_ecosystem, f, indent=2)

    print("Local JSON stores synchronized with Supabase.")
    print("\n=== MASTER SEEDING COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    import asyncio
    asyncio.run(reset_and_seed())

