import sys
import asyncio
sys.path.insert(0, "backend")

from app.services.embedding_service import EmbeddingService
from app.services.recommendation_service import _cosine_similarity

async def main():
    emb = EmbeddingService()
    target = "Secretary and Administrative Assistant: Processing Incoming Mail"
    target_vec = await emb.get_embedding(target)
    
    candidates = [
        ("Unix Mail Server", "Guide to Unix / Explanations / Mail Server Overview. A mail transfer agent transfers electronic mail using SMTP, sendmail, postfix."),
        ("Office Mail", "Business correspondence and office mail handling: sorting incoming postal letters, routing packages, distributing departmental memos."),
        ("Travel Arrangements", "Corporate travel management: booking airline itineraries, hotel reservations, expense policy compliance."),
        ("Ancient Japan", "A History of Japan: The Nara Period and the imperial capital travel routes."),
        ("Medical Physics", "A preference-integrated optimization system for medical physics shift scheduling in radiation oncology."),
    ]
    
    print(f"Target: {target}\n" + "-" * 60)
    for title, text in candidates:
        vec = await emb.get_embedding(f"{title}. {text}")
        score = _cosine_similarity(target_vec, vec)
        print(f"[{score:.4f}] {title}")

if __name__ == "__main__":
    asyncio.run(main())

