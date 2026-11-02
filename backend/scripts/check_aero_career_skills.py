import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.recommendation_service import RecommendationService

rec = RecommendationService()
c_skills = rec.get_cached_career_skills("5b833969-a934-437d-85c5-fa078b105aa4")
print("Total career skills in map for Aerospace Engineer:", len(c_skills))
sample = list(c_skills.items())[:5]
for sid, meta in sample:
    print(f"Skill ID: {sid}, Meta: {meta}")

essential_count = sum(1 for sid, meta in c_skills.items() if meta.get("importance") == "essential")
print("Total essential skills:", essential_count)

