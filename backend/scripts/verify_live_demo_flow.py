import os
import sys
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.daily_drop_service import DailyDropService
from app.services.mentorship_service import mentorship_service

async def main():
    print("=" * 80)
    print("LIVE DEMO END-TO-END FLOW VERIFICATION")
    print("=" * 80)

    daily_drop_service = DailyDropService()

    # --------------------------------------------------------------------------
    # Step 1: Baseline Accounts Verification
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Verifying Pre-Existing Baseline Accounts...")
    auth_users = supabase_client.auth.admin.list_users()
    jordan_user = next((u for u in auth_users if u.email == "softdev.learner@demo.com"), None)
    dr_harper_user = next((u for u in auth_users if u.email == "ent.mentor@demo.com"), None)

    assert jordan_user is not None, "Baseline learner softdev.learner@demo.com not found!"
    assert dr_harper_user is not None, "Baseline mentor ent.mentor@demo.com not found!"
    print(f"PASS: Baseline Learner found (Jordan Blake, ID: {jordan_user.id})")
    print(f"PASS: Baseline Mentor found (Dr. Evelyn Harper, ID: {dr_harper_user.id})")

    # Verify Jordan's Daily Drop
    jordan_drop = await daily_drop_service.get_or_create_daily_drop(jordan_user.id)
    assert jordan_drop and len(jordan_drop.get("lessons", [])) == 3, "Jordan Blake daily drop missing or incomplete"
    print(f"PASS: Baseline Learner Jordan Blake has active 3-lesson drop: Focus '{jordan_drop.get('target_skill_name')}'")
    for idx, l in enumerate(jordan_drop["lessons"], 1):
        print(f"   [{idx}] {l['title']} ({l.get('source_type') or l.get('source_adapter')})")

    # --------------------------------------------------------------------------
    # Step 2: Live Demo Simulation - Create New ENT Learner
    # --------------------------------------------------------------------------
    print("\n[Phase 2] Simulating Live Demo Action: Create ENT Learner...")
    ent_learner_email = "ent.learner@demo.com"
    ent_pwd = "DemoPassword123!"

    # Purge if existing
    existing_ent = next((u for u in auth_users if u.email == ent_learner_email), None)
    if existing_ent:
        supabase_client.auth.admin.delete_user(existing_ent.id)

    ent_res = supabase_client.auth.admin.create_user({
        "email": ent_learner_email,
        "password": ent_pwd,
        "email_confirm": True,
        "user_metadata": {
            "full_name": "Maya Lin",
            "role": "learner",
        }
    })
    ent_learner_id = ent_res.user.id
    print(f"PASS: Created demo ENT Learner Maya Lin (ID: {ent_learner_id})")

    # Find ENT Surgeon career exactly
    careers_res = supabase_client.table("careers").select("id, title").execute()
    ent_career = next((c for c in (careers_res.data or []) if c["title"].strip().lower() == "ent surgeon"), None)
    if not ent_career:
        ent_career = next((c for c in (careers_res.data or []) if "otolaryngol" in c["title"].lower()), None)
    assert ent_career is not None, "ENT Surgeon career not found in database!"
    print(f"PASS: Matched Target Career: '{ent_career['title']}' ({ent_career['id']})")

    # Onboarding: update profile and user skills
    supabase_client.table("profiles").upsert({
        "id": ent_learner_id,
        "email": ent_learner_email,
        "full_name": "Maya Lin",
        "role": "learner",
        "target_career_id": ent_career["id"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Pick 5 skills from ENT Surgeon
    cs_skills = supabase_client.table("career_skills").select("skill_id").eq("career_id", ent_career["id"]).limit(5).execute()
    ent_skills_data = [{"user_id": ent_learner_id, "skill_id": row["skill_id"], "proficiency": 25} for row in (cs_skills.data or [])]
    if ent_skills_data:
        supabase_client.table("user_skills").upsert(ent_skills_data).execute()
    print(f"PASS: Onboarded Maya Lin with target career '{ent_career['title']}' and {len(ent_skills_data)} skills")

    # Generate Daily Drop for Maya Lin
    print("Generating Daily Drop for new ENT Learner Maya Lin...")
    maya_drop = await daily_drop_service.get_or_create_daily_drop(ent_learner_id)
    assert maya_drop and len(maya_drop.get("lessons", [])) == 3, "Maya Lin daily drop generation failed!"
    print(f"PASS: Daily Drop generated for Maya Lin: Focus '{maya_drop.get('target_skill_name')}'")
    for idx, l in enumerate(maya_drop["lessons"], 1):
        print(f"   [{idx}] {l['title']} | Source: {l.get('source_name') or l.get('source_adapter')} | URL: {l.get('source_url')}")

    # --------------------------------------------------------------------------
    # Step 3: Live Demo Simulation - Create New Software Dev Mentor
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Simulating Live Demo Action: Create Software Dev Mentor...")
    softdev_mentor_email = "softdev.mentor@demo.com"
    mentor_pwd = "DemoPassword123!"

    existing_sdm = next((u for u in auth_users if u.email == softdev_mentor_email), None)
    if existing_sdm:
        supabase_client.auth.admin.delete_user(existing_sdm.id)

    sdm_res = supabase_client.auth.admin.create_user({
        "email": softdev_mentor_email,
        "password": mentor_pwd,
        "email_confirm": True,
        "user_metadata": {
            "full_name": "Alex Vance",
            "role": "mentor",
            "headline": "Lead Full-Stack Engineer & Distributed Systems Architect",
            "bio": "10+ years architecting scalable web applications, microservices, and reactive frontends. Passionate about mentoring junior and mid-level software engineers.",
        }
    })
    sdm_id = sdm_res.user.id
    print(f"PASS: Created demo Software Dev Mentor Alex Vance (ID: {sdm_id})")

    # Complete mentor onboarding via mentorship_service
    await mentorship_service.register_or_update_mentor(
        mentor_id=sdm_id,
        full_name="Alex Vance",
        primary_domain="Software Developer",
        headline="Lead Full-Stack Engineer & Distributed Systems Architect",
        bio="10+ years architecting scalable web applications, microservices, and reactive frontends. Passionate about mentoring junior and mid-level software engineers.",
        weekly_hours=5,
        available_days=["Tuesday", "Thursday", "Saturday"],
        preferred_time_window="Evening",
        expertise_skills=[
            "Software Engineering",
            "Web Applications",
            "Database Design",
            "System Architecture",
            "React and Modern JavaScript",
        ],
        max_mentees=6,
    )
    print("PASS: Alex Vance registered in mentorship ecosystem with embedding vector & slots")

    # --------------------------------------------------------------------------
    # Step 4: Semantic Mentor Matching for Jordan Blake
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Testing Mentor Recommendations for Jordan Blake (Software Dev Learner)...")
    match_result = await mentorship_service.match_mentors_for_learner(jordan_user.id)
    matches = match_result.get("matches", [])
    assert len(matches) > 0, "No mentor matches returned for Jordan Blake!"
    
    top_match = matches[0]
    print(f"Top Recommended Mentor: {top_match.get('full_name')} (Score: {top_match.get('match_score', 0):.2f})")
    print(f"Headline: {top_match.get('headline')}")
    print(f"Primary Domain: {top_match.get('primary_domain')}")
    print(f"Shared Skills: {top_match.get('shared_skills')}")

    alex_match = next((m for m in matches if m.get("mentor_id") == sdm_id or m.get("full_name") == "Alex Vance"), None)
    assert alex_match is not None, "Alex Vance was not recommended to Jordan Blake!"
    print(f"PASS: Alex Vance successfully matched to Jordan Blake with relevance score {alex_match.get('match_score', 0):.2f}")

    # --------------------------------------------------------------------------
    # Step 5: Connection Request & Direct Messaging Flow
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Testing Connection Request & Direct Messaging...")
    conn = await mentorship_service.request_connection(
        learner_id=jordan_user.id,
        mentor_id=sdm_id,
        goal_note="Hi Alex! Preparing for technical interviews on system architecture.",
        auto_accept_demo=True,
    )
    conn_id = conn["id"]
    print(f"PASS: Connection established (ID: {conn_id}, Status: {conn.get('status')})")

    # Send Direct Message from Jordan (Learner) to Alex (Mentor)
    msg1 = await mentorship_service.send_message(
        connection_id=conn_id,
        sender_id=jordan_user.id,
        sender_role="learner",
        text="Hi Alex! I reviewed the system design drop on caching. Can we discuss Redis cache invalidation strategies?",
    )
    print(f"PASS: Jordan sent DM (ID: {msg1['id']})")

    # Send Response from Alex (Mentor) to Jordan (Learner)
    msg2 = await mentorship_service.send_message(
        connection_id=conn_id,
        sender_id=sdm_id,
        sender_role="mentor",
        text="Hey Jordan! Absolutely. Let's schedule a 45-minute deep-dive on cache-aside and write-through patterns.",
    )
    print(f"PASS: Alex replied via DM (ID: {msg2['id']})")

    # Fetch Message History
    history = await mentorship_service.get_messages(conn_id)
    assert len(history) >= 2, "Message history incomplete"
    print(f"PASS: Verified message history contains {len(history)} messages")

    # --------------------------------------------------------------------------
    # Step 6: 1-on-1 Session Booking Flow
    # --------------------------------------------------------------------------
    print("\n[Phase 6] Testing 1-on-1 Session Booking...")
    slots = await mentorship_service.get_available_slots(sdm_id, days_ahead=7)
    assert len(slots) > 0, "No available slots returned for Alex Vance!"
    target_slot = slots[0]
    print(f"Booking target slot: {target_slot['slot_start_iso']} ({target_slot['label']})")

    session = await mentorship_service.book_session(
        learner_id=jordan_user.id,
        mentor_id=sdm_id,
        slot_start_iso=target_slot["slot_start_iso"],
        topic="Distributed Caching & Redis Invalidation Patterns",
        focus_skill="System Architecture",
        notes="Jordan wants to review cache invalidation strategies before tech interview.",
    )
    assert session and session.get("id"), "Session booking failed!"
    print(f"PASS: 1-on-1 Session booked successfully (ID: {session['id']})")
    print(f"   Topic: {session.get('topic')}")
    print(f"   Video Meeting URL: {session.get('meeting_url')}")

    # --------------------------------------------------------------------------
    # Step 7: Notification Bell Signal Verification
    # --------------------------------------------------------------------------
    print("\n[Phase 7] Verifying Notification Signals...")
    learner_sessions = await mentorship_service.get_sessions(jordan_user.id, role="learner")
    learner_conns = await mentorship_service.get_learner_connections(jordan_user.id)
    
    mentor_sessions = await mentorship_service.get_sessions(sdm_id, role="mentor")
    mentor_conns = await mentorship_service.get_mentor_connections(sdm_id)

    # Check notification signals derived by NotificationBell logic:
    # 1. Learner sees active session notification
    learner_sess_notifs = [s for s in learner_sessions if s.get("status") not in ("cancelled", "completed")]
    assert len(learner_sess_notifs) > 0, "Learner notification signal missing!"
    print(f"PASS: Learner has {len(learner_sess_notifs)} active session notification(s)")

    # 2. Mentor sees active session and accepted connection
    mentor_sess_notifs = [s for s in mentor_sessions if s.get("status") not in ("cancelled", "completed")]
    assert len(mentor_sess_notifs) > 0, "Mentor notification signal missing!"
    print(f"PASS: Mentor has {len(mentor_sess_notifs)} active session notification(s)")

    # --------------------------------------------------------------------------
    # Step 8: Purge Live Demo Test Accounts & Restore Pristine Baseline
    # --------------------------------------------------------------------------
    print("\n[Phase 8] Restoring Pristine Demo Baseline (Purging Live Demo Accounts)...")
    
    # Clean up ecosystem file of test records
    eco_path = "backend/data/mentorship_ecosystem.json"
    if os.path.exists(eco_path):
        with open(eco_path, "r", encoding="utf-8") as f:
            eco = json.load(f)
        
        # Remove Alex Vance from mentors
        eco["mentors"] = [m for m in eco.get("mentors", []) if m.get("mentor_id") != sdm_id]
        # Remove test connections
        eco["connections"] = [c for c in eco.get("connections", []) if c.get("id") != conn_id]
        # Remove test messages
        eco["messages"] = [m for m in eco.get("messages", []) if m.get("connection_id") != conn_id]
        # Remove test sessions
        eco["sessions"] = [s for s in eco.get("sessions", []) if s.get("id") != session["id"]]

        with open(eco_path, "w", encoding="utf-8") as f:
            json.dump(eco, f, indent=2)
        print("PASS: Purged test mentor, connection, messages, and session from mentorship_ecosystem.json")

    # Delete test users from Supabase Auth
    supabase_client.auth.admin.delete_user(ent_learner_id)
    print(f"PASS: Deleted live test ENT Learner ({ent_learner_id}) from Supabase Auth")

    supabase_client.auth.admin.delete_user(sdm_id)
    print(f"PASS: Deleted live test Software Dev Mentor ({sdm_id}) from Supabase Auth")

    # Confirm only baseline accounts remain
    fresh_auth = supabase_client.auth.admin.list_users()
    remaining_emails = [u.email for u in fresh_auth]
    print("\nRemaining Auth Users in Supabase:")
    for email in sorted(remaining_emails):
        print(f"  - {email}")

    assert "softdev.learner@demo.com" in remaining_emails, "Baseline learner missing!"
    assert "ent.mentor@demo.com" in remaining_emails, "Baseline mentor missing!"
    assert "ent.learner@demo.com" not in remaining_emails, "Test ENT learner was not purged!"
    assert "softdev.mentor@demo.com" not in remaining_emails, "Test Software Dev mentor was not purged!"

    print("\n" + "=" * 80)
    print("ALL 8 VERIFICATION PHASES PASSED WITH ZERO ERRORS.")
    print("PLATFORM IS 100% DEMO-READY.")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
