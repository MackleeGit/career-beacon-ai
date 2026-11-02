import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def find_admins():
    print("--- 1. Querying profiles with role='admin' ---")
    res = supabase_client.table("profiles").select("id, full_name, email, role, created_at").eq("role", "admin").execute()
    admins = res.data or []
    print(f"Found {len(admins)} admin profiles:")
    for a in admins:
        print(f"  ID: {a['id']} | Email: {a.get('email')} | Name: {a.get('full_name')} | Role: {a.get('role')}")

if __name__ == "__main__":
    find_admins()

