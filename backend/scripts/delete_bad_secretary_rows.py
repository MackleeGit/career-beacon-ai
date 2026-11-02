import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

bad_ids = [
    '18a4de4e-7fe0-431a-b371-1095a2a90d77',
    '1eadc0c7-e1ef-448c-a742-46e254e73bd0',
    '72822125-4dd4-4713-8904-39242bee1499'
]

for bid in bad_ids:
    res = supabase_client.table("micro_content").delete().eq("id", bid).execute()
    print(f"Deleted {bid}")

print("Done deleting bad secretary rows.")
