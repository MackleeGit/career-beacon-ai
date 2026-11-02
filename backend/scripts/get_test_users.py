import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

# Find an admin, a mentor, and a learner
admin = supabase_client.table("profiles").select("id, full_name, email, role, target_career_id").eq("role", "admin").limit(1).execute()
mentor = supabase_client.table("profiles").select("id, full_name, email, role").eq("role", "mentor").limit(1).execute()
learners = supabase_client.table("profiles").select("id, full_name, email, role, target_career_id").eq("role", "learner").limit(5).execute()

print("Admin profile:", admin.data)
print("Mentor profile:", mentor.data)
print("Sample Learner profiles:", learners.data)

