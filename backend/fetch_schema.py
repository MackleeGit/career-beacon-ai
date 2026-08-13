import asyncio
from app.core.database import supabase_client

async def fetch_schema():
    res = supabase_client.table("careers").select("*").limit(1).execute()
    print("Careers:", res.data)
    
    # Try fetching a skill
    res = supabase_client.table("skills").select("*").limit(1).execute()
    print("Skills:", res.data)

asyncio.run(fetch_schema())
