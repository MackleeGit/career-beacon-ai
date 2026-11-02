import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

def test_counts():
    cs_count = supabase_client.table("career_skills").select("career_id", count="exact").limit(1).execute()
    print("Exact career_skills total rows in DB:", cs_count.count)

    c_count = supabase_client.table("careers").select("id", count="exact").limit(1).execute()
    print("Exact careers total rows in DB:", c_count.count)

    sk_count = supabase_client.table("skills").select("id", count="exact").limit(1).execute()
    print("Exact skills total rows in DB:", sk_count.count)

if __name__ == "__main__":
    test_counts()

