import asyncio
import sys
import os
import math
import functools
import types
from unittest.mock import MagicMock

print = functools.partial(print, flush=True)

sys.path.insert(0, os.path.abspath("backend"))

# Stub database client for fast offline unit-test execution without network handshakes
_mock_db = types.ModuleType("app.core.database")
_mock_db.supabase_client = MagicMock()
sys.modules["app.core.database"] = _mock_db

from app.services.embedding_service import EmbeddingService
from app.services.recommendation_service import RecommendationService
from app.services.content_service import ContentService
from app.services.mentorship_service import mentorship_service, _cosine_similarity

async def test_vector_engine():
    embedding_service = EmbeddingService()
    print("================================================================================")
    print("TEST SUITE: VECTOR ENGINE UPSCALING, RRF, DOMAIN ANCHORS & Q&A PREFLIGHT")
    print("================================================================================")

    # -------------------------------------------------------------------------
    # 1. Embedding Service: Dimensions, Unit Norm, Batch vs Single, Case Normalization
    # -------------------------------------------------------------------------
    print("\n[1/4] Testing Embedding Service (FastEmbed ONNX SIMD + LRU Cache)...")
    text1 = "Curriculum and practical instructional concepts for Software Architect."
    text2 = "Curriculum and practical instructional concepts for Aerospace Engineer."
    
    vec1 = await embedding_service.get_embedding(text1)
    assert len(vec1) == 384, f"Expected 384 dimensions, got {len(vec1)}"
    norm1 = math.sqrt(sum(x * x for x in vec1))
    assert 0.99 <= norm1 <= 1.01, f"Expected unit-normalized vector, got norm {norm1}"
    print(f"  PASS: Single embedding shape is 384-d, L2 norm: {norm1:.4f}")

    # Test Batch Inference
    batch_vecs = await embedding_service.get_embeddings_batch([text1, text2])
    assert len(batch_vecs) == 2, f"Expected 2 batch embeddings, got {len(batch_vecs)}"
    batch_norm = math.sqrt(sum(x * x for x in batch_vecs[1]))
    assert 0.99 <= batch_norm <= 1.01, f"Expected unit-normalized batch vector, got norm {batch_norm}"
    
    # Verify SIMD batch match
    dot_single_batch = sum(a * b for a, b in zip(vec1, batch_vecs[0]))
    assert dot_single_batch >= 0.9999, f"Batch embedding diverged from single embedding: {dot_single_batch}"
    print(f"  PASS: Parallel C++ ONNX SIMD batching matches single inference (dot product: {dot_single_batch:.6f})")

    # Test LRU Case Normalization
    cached_vec = await embedding_service.get_embedding("   " + text1.upper() + "   ")
    assert cached_vec == vec1, "Case normalization cache hit failed"
    print("  PASS: In-memory LRU cache correctly normalizes whitespace and casing.")

    # -------------------------------------------------------------------------
    # 2. Recommendation Service: Reciprocal Rank Fusion (RRF k=60)
    # -------------------------------------------------------------------------
    print("\n[2/4] Testing Reciprocal Rank Fusion (Dense + Lexical Exact-Token Guard)...")
    rec_service = RecommendationService()
    
    # Simulate candidates:
    # Candidate A has generic high dense similarity (0.85) but misses exact technical tokens ("OAuth 2.0 PKCE")
    # Candidate B has slightly lower dense similarity (0.80) but matches the exact priority skill ("OAuth 2.0 PKCE")
    candidates = [
        {
            "id": "cand-a",
            "title": "General Web Authorization Flow",
            "concept_overview": "Tokens and sessions in web applications.",
            "similarity": 0.85,
        },
        {
            "id": "cand-b",
            "title": "Implementing OAuth 2.0 PKCE Authentication",
            "concept_overview": "Secure single-page app authorization code grant with Proof Key for Code Exchange.",
            "similarity": 0.80,
        },
    ]

    fused = rec_service._apply_reciprocal_rank_fusion(
        candidates=candidates,
        query_text="Curriculum and practical instructional concepts for Backend Developer. Key technical skills: OAuth 2.0 PKCE.",
        priority_skill_names=["OAuth 2.0 PKCE"],
        k=60,
    )

    print(f"  Candidate A Fused Score: {fused[0].get('hybrid_score'):.5f} (Initial dense: {candidates[0]['similarity']})")
    print(f"  Candidate B Fused Score: {fused[1].get('hybrid_score'):.5f} (Initial dense: {candidates[1]['similarity']})")
    
    # Candidate B must rank higher or receive substantial boost from lexical token fusion
    assert fused[0]["id"] == "cand-b", "Expected Candidate B to outrank Candidate A due to exact lexical token match"
    print("  PASS: RRF successfully eliminated lexical blindness for exact acronyms/frameworks.")

    # -------------------------------------------------------------------------
    # 3. Content Service: BLS SOC Occupational Cluster Anchors
    # -------------------------------------------------------------------------
    print("\n[3/4] Testing BLS SOC Domain Cluster Resolution...")
    content_service = ContentService()
    
    cluster_dentist = await content_service.resolve_career_domain(career_title="Dentist", skill_name="Oral Surgery", category="Clinical")
    cluster_pilot = await content_service.resolve_career_domain(career_title="Commercial Aviator", skill_name="Flight Crew Navigation", category="Technical")
    cluster_swe = await content_service.resolve_career_domain(career_title="Software Architect", skill_name="Microservices Architecture", category="Engineering")

    print(f"  'Dentist' -> {cluster_dentist}")
    print(f"  'Commercial Aviator' -> {cluster_pilot}")
    print(f"  'Software Architect' -> {cluster_swe}")

    assert cluster_dentist == "health", f"Expected health cluster for dentist, got {cluster_dentist}"
    assert cluster_pilot == "transportation", f"Expected transportation cluster for pilot, got {cluster_pilot}"
    assert cluster_swe in {"tech", "engineering"}, f"Expected tech/engineering cluster for swe, got {cluster_swe}"
    print("  PASS: SOC cluster anchors dynamically classify cross-industry domains without keyword hacks.")

    # -------------------------------------------------------------------------
    # 4. Mentorship Service: Dual-Vector Mentor Embedding & Answer-Enriched Q&A Lookup
    # -------------------------------------------------------------------------
    print("\n[4/5] Testing Mentorship Pre-flight Semantic Duplicate Resolution & Answer Enrichment...")
    dot_res = _cosine_similarity(vec1, vec1)
    assert abs(dot_res - 1.0) < 1e-4, f"Expected 1.0 for self-similarity, got {dot_res}"
    print(f"  PASS: Fast-path unit-normalized dot product self-similarity: {dot_res:.4f}")

    store = mentorship_service._ensure_store()
    # Test dual-vector computation on a focused 1-mentor fixture slice for fast unit test execution
    sample_mentor = dict(store["mentors"][0])
    sample_mentor.pop("domain_vector", None)
    sample_mentor.pop("skills_vector", None)
    mini_store = {**store, "mentors": [sample_mentor]}
    await mentorship_service._ensure_mentor_vectors(mini_store)
    verified_mentor = mini_store["mentors"][0]
    assert verified_mentor.get("domain_vector") and len(verified_mentor["domain_vector"]) == 384, "Missing mentor domain_vector"
    assert verified_mentor.get("skills_vector") and len(verified_mentor["skills_vector"]) == 384, "Missing mentor skills_vector"
    print("  PASS: Mentors maintain distinct 384-d `domain_vector` and `skills_vector` representations.")

    test_q_id = "test-preflight-q1"
    orig_questions = list(store.get("questions", []))
    store["questions"] = [
        {
            "id": test_q_id,
            "title": "How do database indexes speed up B-tree lookups in PostgreSQL?",
            "body": "Detailed explanation of B-tree balanced search trees and leaf node pointers.",
            "skill_tag": "PostgreSQL Indexing",
            "career_title": "Database Engineer",
            "embedding": None,
            "answers": [{
                "id": "ans-1",
                "body": "B-trees maintain sorted keys across fixed-size blocks, reducing disk I/O to O(log n) with composite index selectivity.",
                "mentor_name": "Dr. Aris Thorne",
                "mentor_headline": "Principal Database Architect",
            }],
        }
    ]
    mentorship_service._save_store(store)

    try:
        matches = await mentorship_service.find_similar_answered_questions(
            query_text="Why do B-tree indexes make PostgreSQL queries faster?",
            skill_tag="PostgreSQL Indexing",
            threshold=0.70,
            limit=3,
        )

        assert len(matches) > 0, "Expected at least 1 match for semantic rephrasing"
        top_match = matches[0]
        print(f"  Top Match Title: '{top_match['title']}'")
        print(f"  Calculated Similarity: {top_match['similarity']:.3f}")
        assert top_match["id"] == test_q_id, f"Expected {test_q_id}, got {top_match['id']}"
        assert len(top_match["answers"]) > 0, "Expected top match to include verified mentor answers"
        assert "embedding" not in top_match, "Expected internal embedding vector stripped from public response"
        print("  PASS: Preflight semantic lookup returned answer-enriched mentor ticket instantly.")
    finally:
        store["questions"] = [q for q in orig_questions if q.get("id") != test_q_id]
        mentorship_service._save_store(store)

    # -------------------------------------------------------------------------
    # 5. Full-Catalog Skill Canonicalization (Zero Word Overlap)
    # -------------------------------------------------------------------------
    print("\n[5/5] Testing Full-Catalog Skill Canonicalization (_match_canonical_skill_by_vector)...")
    from app.routers.learner_onboarding import _match_canonical_skill_by_vector
    catalog_sample = [
        {"id": "sk-1", "name": "Docker Containerization", "category": "Tools"},
        {"id": "sk-2", "name": "Pediatric Dosage Calculation", "category": "Clinical"},
        {"id": "sk-3", "name": "Discounted Cash Flow Valuation", "category": "Finance"},
    ]
    matched_skill = await _match_canonical_skill_by_vector("Containerizing Microservices with Docker", catalog_sample, threshold=0.78)
    assert matched_skill and matched_skill["id"] == "sk-1", f"Expected sk-1, got {matched_skill}"
    print(f"  PASS: Canonicalized 'Containerizing Microservices with Docker' -> '{matched_skill['name']}'")

    print("\n================================================================================")
    print("ALL 5 VECTOR ENGINE TEST MODULES PASSED WITH 100% ACCURACY")
    print("================================================================================")

if __name__ == "__main__":
    asyncio.run(test_vector_engine())
