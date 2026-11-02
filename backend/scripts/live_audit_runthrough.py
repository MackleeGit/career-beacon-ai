import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.content_service import ContentService

BASE_URL = "http://127.0.0.1:8000"

async def run_live_audit():
    print("=" * 70)
    print("STARTING LIVE END-TO-END SYSTEM RUNTHROUGH & BUG AUDIT (V2)")
    print("=" * 70)

    # 1. Sign in as Admin
    print("\n[STEP 1: AUTHENTICATION]")
    try:
        auth_res = supabase_client.auth.sign_in_with_password({
            "email": "admin@careerbeacon.internal",
            "password": "AdminPassword123!"
        })
        token = auth_res.session.access_token
        admin_id = auth_res.user.id
        print(f"  * Admin authenticated: {admin_id[:8]}... (Token obtained)")
    except Exception as e:
        print(f"  * FAILED to sign in as admin: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 2. Public Health Check
        print("\n[STEP 2: PUBLIC HEALTH CHECK]")
        r_health = await client.get(f"{BASE_URL}/health")
        print(f"  * GET /health -> Status: {r_health.status_code} | Body: {r_health.json()}")
        assert r_health.status_code == 200

        # 3. Admin System Stats
        print("\n[STEP 3: ADMIN SYSTEM STATS]")
        r_stats = await client.get(f"{BASE_URL}/api/admin/stats", headers=headers)
        print(f"  * GET /api/admin/stats -> Status: {r_stats.status_code}")
        if r_stats.status_code == 200:
            stats = r_stats.json().get("stats", {})
            print(f"    - Total users in DB: {stats.get('total_users')}")
            print(f"    - Learners: {stats.get('learner_count')} | Mentors: {stats.get('mentor_count')}")
            print(f"    - Careers total: {stats.get('total_careers')} | Pending review: {stats.get('unreviewed_careers')}")
            print(f"    - Total sessions: {stats.get('total_sessions')} | Connections: {stats.get('active_connections')}")
        else:
            print(f"    - ERROR: {r_stats.text}")
        assert r_stats.status_code == 200

        # 4. Admin Moderation Desk
        print("\n[STEP 4: ADMIN MODERATION DESK]")
        r_mod = await client.get(f"{BASE_URL}/api/admin/moderation/flagged", headers=headers)
        print(f"  * GET /api/admin/moderation/flagged -> Status: {r_mod.status_code}")
        if r_mod.status_code == 200:
            items = r_mod.json().get("flagged_items", [])
            print(f"    - Flagged items in moderation queue: {len(items)}")
        else:
            print(f"    - ERROR: {r_mod.text}")
        assert r_mod.status_code == 200

        # 5. In-App Content Moderation Flagging
        print("\n[STEP 5: IN-APP CONTENT FLAGGING]")
        flag_payload = {
            "item_type": "message",
            "item_id": "msg-test-audit-1",
            "content_snippet": "Spam promotional link: http://buycrypto-token-fast.biz",
            "target_context": "Direct Message to Mentor",
            "reason": "Test audit: testing moderation flag submission pipeline",
        }
        r_flag = await client.post(f"{BASE_URL}/api/admin/moderation/flag", json=flag_payload, headers=headers)
        print(f"  * POST /api/admin/moderation/flag -> Status: {r_flag.status_code}")
        if r_flag.status_code == 200:
            print(f"    - Flag confirmed: {r_flag.json().get('flag_id')}")
        else:
            print(f"    - ERROR: {r_flag.text}")
        assert r_flag.status_code == 200

        # 6. Recommendation Feedback Submission (like, dislike, irrelevant)
        print("\n[STEP 6: RECOMMENDATION FEEDBACK SUBMISSION]")
        feedback_payload = {
            "lesson_id": "test-lesson-id-100",
            "feedback": "like",
            "lesson_title": "Test Lesson on Key Values"
        }
        r_fb = await client.post(f"{BASE_URL}/api/recommendations/feedback", json=feedback_payload, headers=headers)
        print(f"  * POST /api/recommendations/feedback (like) -> Status: {r_fb.status_code}")
        if r_fb.status_code == 200:
            print(f"    - Feedback recorded: {r_fb.json().get('message')}")
        else:
            print(f"    - ERROR: {r_fb.text}")
        assert r_fb.status_code == 200

        # Test 'irrelevant' feedback (auto-flags to moderation desk)
        irr_payload = {
            "lesson_id": "test-lesson-id-101",
            "feedback": "irrelevant",
            "lesson_title": "Off-Topic Calculus Module",
            "reason": "Irrelevant to medical clinical training"
        }
        r_irr = await client.post(f"{BASE_URL}/api/recommendations/feedback", json=irr_payload, headers=headers)
        print(f"  * POST /api/recommendations/feedback (irrelevant) -> Status: {r_irr.status_code}")
        if r_irr.status_code == 200:
            print(f"    - Auto-flag to moderation recorded: {r_irr.json().get('message')}")
        else:
            print(f"    - ERROR: {r_irr.text}")
        assert r_irr.status_code == 200

        # Verify that moderation desk now contains the flagged items
        r_mod_updated = await client.get(f"{BASE_URL}/api/admin/moderation/flagged", headers=headers)
        new_count = len(r_mod_updated.json().get("flagged_items", []))
        print(f"    - Verified moderation queue updated: {new_count} items now in desk")
        assert new_count >= 2

        # 7. Mentorship Mentors Listing (Admin & Learner)
        print("\n[STEP 7: MENTORSHIP ECOSYSTEM]")
        r_admin_mentors = await client.get(f"{BASE_URL}/api/admin/mentors", headers=headers)
        print(f"  * GET /api/admin/mentors -> Status: {r_admin_mentors.status_code}")
        if r_admin_mentors.status_code == 200:
            m_list = r_admin_mentors.json().get("mentors", [])
            print(f"    - Total active mentors returned: {len(m_list)}")
            for m in m_list[:3]:
                print(f"      * {m.get('full_name')} [{m.get('primary_domain')}]")
        assert r_admin_mentors.status_code == 200

        # Learner matches endpoint
        r_matches = await client.get(f"{BASE_URL}/api/mentor/matches", headers=headers)
        print(f"  * GET /api/mentor/matches -> Status: {r_matches.status_code}")
        if r_matches.status_code == 200:
            matches = r_matches.json().get("matches", [])
            print(f"    - Semantic mentor matches: {len(matches)}")
        assert r_matches.status_code == 200

        # 8. Mentorship Community Pulse
        print("\n[STEP 8: MENTORSHIP COMMUNITY PULSE]")
        r_pulse = await client.get(f"{BASE_URL}/api/mentor/pulse", headers=headers)
        print(f"  * GET /api/mentor/pulse -> Status: {r_pulse.status_code}")
        if r_pulse.status_code == 200:
            posts = r_pulse.json().get("posts", [])
            print(f"    - Total pulse discussions: {len(posts)}")
            for p in posts[:2]:
                print(f"      * [{p.get('post_type')}] {p.get('title')} (by {p.get('mentor_name')})")
        assert r_pulse.status_code == 200

        # 9. Session Booking Validation (Past date & 24-hr notice rejection)
        print("\n[STEP 9: SESSION BOOKING VALIDATION CONSTRAINTS]")
        # A: Past date booking attempt
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        booking_past = {
            "mentor_id": "cb9d2d92-1d70-4175-9058-ea88a071881f",
            "slot_start_iso": past_time,
            "topic": "Audit past booking rejection"
        }
        r_past = await client.post(f"{BASE_URL}/api/mentor/sessions/book", json=booking_past, headers=headers)
        print(f"  * Booking in the past -> Status: {r_past.status_code} (Expected 400)")
        if r_past.status_code == 400:
            print(f"    - Correctly rejected with: '{r_past.json().get('detail')}'")
        else:
            print(f"    - UNEXPECTED RESPONSE: {r_past.status_code} {r_past.text}")
        assert r_past.status_code == 400

        # B: Within 24 hours notice attempt
        near_future = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        booking_short = {
            "mentor_id": "cb9d2d92-1d70-4175-9058-ea88a071881f",
            "slot_start_iso": near_future,
            "topic": "Audit 24-hr notice rejection"
        }
        r_short = await client.post(f"{BASE_URL}/api/mentor/sessions/book", json=booking_short, headers=headers)
        print(f"  * Booking within 24 hours -> Status: {r_short.status_code} (Expected 400)")
        if r_short.status_code == 400:
            print(f"    - Correctly rejected with: '{r_short.json().get('detail')}'")
        else:
            print(f"    - UNEXPECTED RESPONSE: {r_short.status_code} {r_short.text}")
        assert r_short.status_code == 400

        # 10. JIT Adapter Live Verification (OWASP for Information Security Analyst)
        print("\n[STEP 10: UNSEEDED CAREER JIT FRONTIER INDUCTION CHECK]")
        cs = ContentService()
        source_res = await cs.fetch_live_source_for_skill(
            skill_name="Conduct Vulnerability Scanning",
            category="Security Operations",
            career_title="Information Security Analyst"
        )
        if source_res and source_res.get("source_adapter") == "owasp":
            print(f"  * OWASP Adapter successfully resolved:")
            print(f"    - Title: {source_res.get('title')}")
            print(f"    - Source: {source_res.get('source')}")
            print(f"    - Trust Score: {source_res.get('trust_score')}")
            print(f"    - Raw Text characters: {len(source_res.get('raw_text', ''))}")
        assert source_res.get("source_adapter") == "owasp"

    print("\n" + "=" * 70)
    print("ALL 10 LIVE AUDIT GATES PASSED WITH ZERO EXCEPTIONS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_live_audit())
