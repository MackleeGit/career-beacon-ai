import sys
import asyncio
sys.path.insert(0, "backend")

from app.services.embedding_service import EmbeddingService
from app.services.recommendation_service import _cosine_similarity

async def main():
    emb = EmbeddingService()
    target = "Secretary and Administrative Assistant: Coordinating Travel Arrangements"
    t_vec = await emb.get_embedding(target)
    
    test_articles = [
        ("Cartesian coordinate robot", "A Cartesian coordinate robot is an industrial robot whose three principal axes of control are linear and are at right angles to each other."),
        ("Road manager", "A road manager is the person who handles the business and logistics for a band, musician, or dance company while they are on tour."),
        ("Corporate travel management", "Corporate travel management is the function of managing a company's strategic approach to travel, the negotiations with all vendors, day-to-day operation of the corporate travel program, traveler safety and security, credit-card management and travel and expenses data management."),
        ("Business travel itinerary", "Preparing executive travel itineraries, booking flights and hotels, aligning ground transportation and managing expense receipts for executive assistants."),
    ]
    
    print(f"Target: {target}\n" + "-" * 70)
    for title, text in test_articles:
        vec = await emb.get_embedding(f"{title}: {text}")
        score = _cosine_similarity(t_vec, vec)
        print(f"[{score:.4f}] {title}")

if __name__ == "__main__":
    asyncio.run(main())

