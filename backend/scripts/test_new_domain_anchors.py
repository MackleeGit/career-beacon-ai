import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.embedding_service import EmbeddingService

async def test_new_anchors():
    es = EmbeddingService()
    anchors = {
        "health": "healthcare medicine clinical medical doctor surgery nursing dental oral pharmacology hospital patient biology anatomy",
        "tech": "software programming technology web development cloud computer code database api network algorithms",
        "engineering": "aerospace engineering mechanical electrical civil propulsion avionics thermodynamics fluid structural robotics aeronautics CAD materials",
        "science": "biology chemistry physics laboratory scientific research genetics biochemistry environmental earth",
        "security": "cybersecurity information security vulnerability penetration testing access control incident response cryptography",
        "finance": "finance accounting banking financial economics corporate budget taxation balance sheet valuation audit investments revenue",
        "business_admin": "office administration secretary executive assistant business travel coordination scheduling clerical workplace management corporate operations administrative logistics customer communication reception office technology",
        "safety_trades": "occupational workplace safety hazard compliance construction electrical wiring mechanical trades industrial osha",
        "transportation": "aviation pilot aircraft flight navigation aerospace transportation maritime logistics vessel air traffic control flight deck cockpit",
    }
    vectors = {}
    for d, text in anchors.items():
        vectors[d] = await es.get_embedding(text)

    for query in [
        "Secretary and Administrative Assistant Coordinating Travel Arrangements",
        "Secretary and Administrative Assistant Managing Calendar Scheduling",
        "Aerospace Engineer Propulsion System Performance Testing",
        "Web Developer JavaScript (ES6+)",
        "Dentists, General Dental Cleaning"
    ]:
        q_vec = await es.get_embedding(query)
        scores = {d: sum(x * y for x, y in zip(q_vec, v)) for d, v in vectors.items()}
        best = max(scores, key=scores.get)
        print(f"Query: '{query}' -> Best Domain: {best} (score: {scores[best]:.3f})")

asyncio.run(test_new_anchors())
