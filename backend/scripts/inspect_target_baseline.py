import sys
sys.path.insert(0, "backend")

from app.core.database import supabase_client

# Check mentors in mentors table
m_res = supabase_client.table("mentors").select("*").execute()
print(f"Total mentors in mentors table: {len(m_res.data)}")
for m in m_res.data:
    print(m)

# Check test baseline users
u_res = supabase_client.table("profiles").select("id, full_name, role, target_career_id").in_("id", ["5e2bca7f-8ac8-457e-9c40-cd1a09d07d0a", "cb9d2d92-1d70-4175-9058-ea88a071881f"]).execute()
print("\nTarget Baseline Profiles:")
for p in u_res.data:
    print(p)
