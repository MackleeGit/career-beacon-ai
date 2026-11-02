import asyncio
import os
import sys

# Ensure stdout encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.content_service import ContentService

SEEDS = [
    {
        "career_title": "Registered Nurse",
        "skills": [
            {"name": "Medication administration", "category": "Clinical Practice"},
            {"name": "Wound assessment & dressing", "category": "Clinical Practice"},
        ]
    },
    {
        "career_title": "Accountant and Auditor",
        "skills": [
            {"name": "prepare financial statements", "category": "Financial Reporting"},
            {"name": "Perform Variance Analysis", "category": "Management Accounting"},
        ]
    },
    {
        "career_title": "Software Developer",
        "skills": [
            {"name": "Computers and Electronics", "category": "Engineering & Technology"},
        ]
    }
]

async def seed_demo_baseline():
    content_service = ContentService()
    print("=" * 70)
    print("SEEDING CURATED DEMO BASELINE LESSONS")
    print("=" * 70)

    for entry in SEEDS:
        career_title = entry["career_title"]
        print(f"\nTarget Career: {career_title}")

        # Fetch career ID
        c_res = supabase_client.table("careers").select("id").eq("title", career_title).limit(1).execute()
        if not c_res.data:
            print(f"  [SKIP] Career '{career_title}' not found in database.")
            continue
        career_id = c_res.data[0]["id"]

        for sk_target in entry["skills"]:
            sk_name = sk_target["name"]
            sk_cat = sk_target["category"]

            # Lookup skill_id in database
            sk_res = supabase_client.table("skills").select("id, name").ilike("name", f"%{sk_name}%").limit(1).execute()
            if not sk_res.data:
                print(f"  [SKIP] Skill '{sk_name}' not found in database.")
                continue
            skill_id = sk_res.data[0]["id"]
            actual_name = sk_res.data[0]["name"]

            # Check if lesson already exists
            existing = supabase_client.table("micro_content").select("id, title").eq("associated_skill_id", skill_id).execute()
            if existing.data:
                print(f"  [EXISTS] Lesson already in micro_content for '{actual_name}' (ID: {existing.data[0]['id'][:8]}...)")
                continue

            print(f"  [GENERATING] Ingesting & synthesizing lesson for '{actual_name}' ({career_title})...")
            try:
                lesson = await content_service.generate_dynamic_lesson_for_skill(
                    skill_id=skill_id,
                    skill_name=actual_name,
                    category=sk_cat,
                    career_title=career_title,
                    target_proficiency=20,
                )
                if lesson and lesson.get("id"):
                    print(f"  [SUCCESS] Created: '{lesson.get('title')}'")
                    print(f"            Source: {lesson.get('source_name')} | Quizzes: {len(lesson.get('quizzes') or [])} MCQs")
                else:
                    print(f"  [WARNING] Generation returned None for '{actual_name}' (fell through filters).")
            except Exception as e:
                print(f"  [ERROR] Failed to generate for '{actual_name}': {e}")

            # Politeness delay between LLM & scraping requests
            await asyncio.sleep(1.0)

    print("\n" + "=" * 70)
    print("DEMO BASELINE SEEDING COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(seed_demo_baseline())

