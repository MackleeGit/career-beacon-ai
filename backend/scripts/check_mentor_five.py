import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

res = supabase_client.table("profiles").select("id, full_name, email, role, target_career_id").ilike("full_name", "%Mentor%").execute()
print("Profiles with 'Mentor':", res.data)

all_mentors_table = supabase_client.table("mentors").select("id, profile_id, bio, expertise").execute()
print("\nMentors table rows:", all_mentors_table.data)
