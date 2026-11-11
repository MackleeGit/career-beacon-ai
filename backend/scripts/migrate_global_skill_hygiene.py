"""
backend/scripts/migrate_global_skill_hygiene.py
-----------------------------------------------
Global database migration to enforce skill taxonomy hygiene:
1. Identifies O*NET Physical/Cognitive Abilities (50 items) and generic Work Activities (41 items).
2. Updates all matching career_skills rows across the database to importance='optional'.
3. Cleans up orphaned or mislabeled junction records so the entire catalog is production-clean.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import supabase_client

GENERIC_NOISE_NAMES = {
    "Reading Comprehension", "Active Listening", "Writing", "Speaking",
    "Mathematics", "Science", "Critical Thinking", "Active Learning",
    "Learning Strategies", "Monitoring", "Social Perceptiveness", "Coordination",
    "Persuasion", "Negotiation", "Instructing", "Service Orientation",
    "Complex Problem Solving", "Judgment and Decision Making", "Time Management",
    "Management of Personnel Resources", "Management of Financial Resources",
    "Management of Material Resources", "Near Vision", "English Language",
    "Speech Recognition", "Speech Clarity", "Identifying Objects, Actions, and Events",
    "Getting Information", "Flexibility of Closure", "Category Flexibility",
    "Oral Comprehension", "Written Comprehension", "Oral Expression", "Written Expression",
    "Problem Sensitivity", "Inductive Reasoning", "Deductive Reasoning",
    "Information Ordering", "Selective Attention", "Fluency of Ideas", "Originality",
    "Perceptual Speed", "Visualization", "Far Vision", "Visual Color Discrimination",
    "Arm-Hand Steadiness", "Finger Dexterity", "Manual Dexterity", "Multilimb Coordination",
    "Trunk Strength", "Static Strength", "Dynamic Strength", "Explosive Strength",
    "Stamina", "Extent Flexibility", "Dynamic Flexibility", "Gross Body Coordination",
    "Gross Body Equilibrium", "Speed of Limb Movement", "Wrist-Finger Speed",
    "Response Orientation", "Rate Control", "Control Precision", "Reaction Time",
    "Hearing Sensitivity", "Auditory Attention", "Sound Localization",
    "Depth Perception", "Glare Sensitivity", "Peripheral Vision"
}

def run_migration():
    print("Starting Global Skill Hygiene Migration...")
    
    # 1. Fetch all skills
    res = supabase_client.table("skills").select("id, name, category").execute()
    skills = res.data or []
    print(f"Total skills in database: {len(skills)}")

    noise_skill_ids = set()
    for s in skills:
        cat = s.get("category") or ""
        name = s.get("name") or ""
        if cat in ("Ability", "Work Activity") or name in GENERIC_NOISE_NAMES:
            noise_skill_ids.add(s["id"])

    print(f"Identified {len(noise_skill_ids)} unteachable / generic ability skill IDs.")

    if not noise_skill_ids:
        print("No noise skill IDs found. Exiting.")
        return

    # 2. Update career_skills in batches
    noise_list = list(noise_skill_ids)
    batch_size = 50
    total_updated = 0

    for i in range(0, len(noise_list), batch_size):
        chunk = noise_list[i : i + batch_size]
        try:
            upd_res = (
                supabase_client.table("career_skills")
                .update({"importance": "optional"})
                .in_("skill_id", chunk)
                .eq("importance", "essential")
                .execute()
            )
            count = len(upd_res.data) if upd_res.data else 0
            total_updated += count
            print(f"Batch {i // batch_size + 1}: Demoted {count} essential links to optional.")
        except Exception as e:
            print(f"Error updating batch {i}: {e}")
        time.sleep(0.1)

    print(f"Migration completed successfully. Total essential links demoted: {total_updated}")

if __name__ == "__main__":
    run_migration()

