import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client
from app.services.recommendation_service import RecommendationService

async def test_dentist_recomms():
    # Find Dentist career
    c_res = supabase_client.table("careers").select("id, title").ilike("title", "%Dentist%").execute()
    print("Dentist careers found:")
    for c in c_res.data:
        print(f"  - {c['title']} ({c['id']})")

    if not c_res.data:
        return
    dentist_id = c_res.data[0]["id"]
    dentist_title = c_res.data[0]["title"]

    # Check skills for this career
    cs_res = supabase_client.table("career_skills").select("skill_id, importance, skills(name, category)").eq("career_id", dentist_id).eq("importance", "essential").execute()
    print(f"\nEssential skills for {dentist_title}: {len(cs_res.data or [])}")
    for r in (cs_res.data or [])[:5]:
        print(f"  * {r['skills']['name']} [{r['skills']['category']}]")

    # Let's time recommendation generation for a test profile enrolled in this career
    # First, let's see which user has target_career_id = dentist_id, or create/temporarily assign
    rec_service = RecommendationService()
    # Check if a user is enrolled in dentist
    p_res = supabase_client.table("profiles").select("id").eq("target_career_id", dentist_id).limit(1).execute()
    user_id = p_res.data[0]["id"] if p_res.data else None
    print(f"\nUser enrolled in Dentist: {user_id}")

    if not user_id:
        # Let's see what happens if we query recommendations for carltest or admin
        p_any = supabase_client.table("profiles").select("id").limit(1).execute()
        user_id = p_any.data[0]["id"]
        # temporarily test recommendations logic
        print(f"Using profile {user_id}")

if __name__ == "__main__":
    asyncio.run(test_dentist_recomms())
