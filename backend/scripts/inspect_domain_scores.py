import sys
import asyncio
sys.path.insert(0, "backend")

from app.services.content_service import ContentService

async def main():
    cs = ContentService()
    # Trigger vector initialization
    await cs.resolve_career_domain("test", "test")
    
    # Test with enriched tech anchor
    enriched_tech = "software programming technology web development cloud computer code database api network algorithms operating systems sysadmin linux unix server infrastructure"
    cs._domain_anchor_vectors["tech"] = await cs.embedding_service.get_embedding(enriched_tech)
    
    query = "Business correspondence and office mail handling"
    q_vec = await cs.embedding_service.get_embedding(query)
    
    scores = {
        d: sum(x * y for x, y in zip(q_vec, v))
        for d, v in cs._domain_anchor_vectors.items()
    }
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print(f"Scores for '{query}':")
    for d, s in sorted_scores:
        print(f"  {d}: {s:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
