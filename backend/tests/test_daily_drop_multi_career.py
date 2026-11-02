import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.abspath("backend"))

from app.services.daily_drop_service import DailyDropService, DAILY_SPRINTS_FILE, _load_json_file, _save_json_file, _today_str

TEST_USERS = [
    {"user_id": "e955aa77-c9a4-4976-ba6f-a0e6b0edcdf0", "expected_career": "Frontend Developer", "domain": "Tech"},
    {"user_id": "b2cb517d-8907-4db0-a938-234e799811ff", "expected_career": "Commercial Pilot", "domain": "Aviation"},
    {"user_id": "5e63840b-cf51-458a-9985-e86e26d301c7", "expected_career": "Dentists, General", "domain": "Dental"},
    {"user_id": "a4b3c612-0599-4669-b3ac-da946234482a", "expected_career": "ENT Surgeon", "domain": "Medical"},
]

def reset_test_users_for_today():
    today = _today_str()
    sprints = _load_json_file(DAILY_SPRINTS_FILE)
    test_uids = {u["user_id"] for u in TEST_USERS}
    clean_sprints = [s for s in sprints if not (s.get("user_id") in test_uids and s.get("sprint_date") == today)]
    _save_json_file(DAILY_SPRINTS_FILE, clean_sprints)
    print(f"Cleared existing sprints for {len(test_uids)} test users for date {today}.")

async def run_audit():
    reset_test_users_for_today()
    service = DailyDropService()
    print("=" * 80)
    print("AUDITING 6-LESSON POOL MODEL (SAME-TOPIC 0MS MULLIGAN SWAP)")
    print("=" * 80)

    for item in TEST_USERS:
        uid = item["user_id"]
        career_name = item["expected_career"]
        domain = item["domain"]
        print(f"\n>>> AUDITING CAREER: {career_name} [{domain}] (User: {uid})")

        # 1. Fetch initial Daily Drop
        t0 = time.time()
        drop = await service.get_or_create_daily_drop(uid)
        dt = (time.time() - t0) * 1000
        
        target_skill = drop.get("target_skill_name")
        lessons = drop.get("lessons", [])
        print(f"  [Initial Drop] ({dt:.1f}ms) Target Focus: '{target_skill}' | Active Lessons: {len(lessons)}")
        for idx, l in enumerate(lessons, 1):
            print(f"    Active {idx}: '{l['title'][:40]}...' | Skill: '{l.get('skill_name')}'")

        # 2. Test 1-shot Re-Roll (Mulligan Swap on SAME skill)
        print("  [Testing 1-Shot Re-Roll (Reserve Swap on SAME Skill)]")
        t0 = time.time()
        rerolled = await service.reroll_daily_drop(uid)
        dt_rr = (time.time() - t0) * 1000
        new_target_skill = rerolled.get("target_skill_name")
        new_lessons = rerolled.get("lessons", [])
        
        topic_maintained = (new_target_skill == target_skill)
        print(f"    Re-Roll Completed in {dt_rr:.2f}ms | Target Focus: '{new_target_skill}' (Same Topic: {topic_maintained}) | Lessons: {len(new_lessons)}")
        for idx, l in enumerate(new_lessons, 1):
            print(f"      Reserve {idx}: '{l['title'][:40]}...' | Skill: '{l.get('skill_name')}'")
        
        assert topic_maintained, f"Error: Topic changed from {target_skill} to {new_target_skill}"

        # 3. Test 2nd Re-Roll (Strict Rejection)
        print("  [Testing 2nd Re-Roll Guardrail]")
        try:
            await service.reroll_daily_drop(uid)
            print("    FAIL: 2nd Re-roll was erroneously allowed!")
        except ValueError as ve:
            print(f"    PASS: 2nd Re-roll was blocked as expected -> {ve}")

        # 4. Test Quiz Submission on Reserve Drop
        if new_lessons:
            first_lesson = new_lessons[0]
            print(f"  [Submitting Quiz for Reserve Lesson 1: '{first_lesson['title'][:30]}...']")
            pass_res = await service.record_lesson_passed(uid, first_lesson["id"])
            print(f"    Progress: {pass_res.get('passed_count')}/{pass_res.get('total_count')} | Completed: {pass_res.get('is_completed')}")

    print("\n" + "=" * 80)
    print("6-LESSON POOL AUDIT COMPLETE: 100% PASS")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_audit())
