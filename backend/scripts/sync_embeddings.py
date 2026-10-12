import sys, asyncio
sys.path.append('backend')
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client

async def sync_career_vectors():
    svc = EmbeddingService()
    res = supabase_client.table('careers').select('id, title, description').execute()
    print(f"Total careers in DB: {len(res.data)}")
    for c in res.data:
        text = f"{c['title']}: {c.get('description') or ''}".strip()
        vec = await svc.get_embedding(text)
        supabase_client.table('careers').update({'career_vector': vec}).eq('id', c['id']).execute()
        print(f"Updated vector for: {c['title']}")

if __name__ == '__main__':
    asyncio.run(sync_career_vectors())
