import os
import asyncio
from typing import Optional, List, Dict
from collections import OrderedDict

# Prevent Rust tokenizers (Rayon) threadpool deadlocks on Windows / Job Objects
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastembed import TextEmbedding

# Module-level shared singleton to ensure only ONE ONNX model instance is loaded in RAM
_shared_model: Optional[TextEmbedding] = None

# In-memory LRU cache for text embeddings (max 4096 entries)
_embedding_cache: OrderedDict[str, List[float]] = OrderedDict()
_CACHE_MAX_SIZE = 4096

# In-memory canonical skill vector cache (skill_id -> 384-d unit vector)
_canonical_skill_vector_cache: Dict[str, List[float]] = {}
SKILL_CANONICALIZATION_THRESHOLD = 0.82


def _get_model() -> TextEmbedding:
    global _shared_model
    if _shared_model is None:
        # Prefer cached local snapshot first to eliminate remote network handshake latency (~30s timeout when offline)
        try:
            _shared_model = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                threads=2,
                local_files_only=True
            )
        except Exception:
            _shared_model = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                threads=2
            )
    return _shared_model


def _run_embed_sync(model: TextEmbedding, texts: List[str]) -> List[List[float]]:
    """Synchronous CPU-bound inference helper."""
    return [next(model.embed([t])).tolist() for t in texts]


class EmbeddingService:
    def __init__(self):
        # Lightweight wrapper; model is loaded on-demand via singleton
        pass

    @property
    def model(self) -> TextEmbedding:
        return _get_model()

    def get_embedding_sync(self, text: str) -> List[float]:
        """Synchronous embedding lookup leveraging local LRU cache with immediate fallback to ONNX SIMD."""
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")

        cache_key = text.strip().lower()
        if cache_key in _embedding_cache:
            _embedding_cache.move_to_end(cache_key)
            return _embedding_cache[cache_key]

        results = _run_embed_sync(self.model, [text.strip()])
        embedding = results[0]

        if len(_embedding_cache) >= _CACHE_MAX_SIZE:
            _embedding_cache.popitem(last=False)
        _embedding_cache[cache_key] = embedding

        return embedding

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional vector embedding for the input text.
        Uses in-memory case-normalized LRU cache (~0.02ms hit) and direct C++ ONNX SIMD (~10ms cold).
        Note: Runs directly without Python ThreadPoolExecutor wrapper because Rust `tokenizers` (Rayon)
        and ONNXRuntime intra-op threadpools manage native C++/Rust threads internally and can deadlock
        when invoked across Python ThreadPoolExecutor threads on Windows.
        """
        return self.get_embedding_sync(text)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-generates 384-dimensional vector embeddings for multiple texts using FastEmbed SIMD.
        Resolves cached items first and only executes ONNX inference for cache misses.
        """
        if not texts:
            return []

        clean_texts = [t.strip() for t in texts]
        cache_keys = [t.lower() for t in clean_texts]

        # Check cache
        results: List[Optional[List[float]]] = [None] * len(clean_texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        for idx, key in enumerate(cache_keys):
            if key in _embedding_cache:
                _embedding_cache.move_to_end(key)
                results[idx] = _embedding_cache[key]
            else:
                missing_indices.append(idx)
                missing_texts.append(clean_texts[idx])

        # Compute missing embeddings in one SIMD-vectorized C++ ONNX batch
        if missing_texts:
            computed_vectors = _run_embed_sync(self.model, missing_texts)
            for idx, key, vec in zip(missing_indices, [cache_keys[i] for i in missing_indices], computed_vectors):
                results[idx] = vec
                if len(_embedding_cache) >= _CACHE_MAX_SIZE:
                    _embedding_cache.popitem(last=False)
                _embedding_cache[key] = vec

        return [vec for vec in results if vec is not None]

    async def match_canonical_skill(
        self,
        raw_name: str,
        existing_skills: List[Dict],
        threshold: float = SKILL_CANONICALIZATION_THRESHOLD,
    ) -> Optional[Dict]:
        """
        Full-catalog semantic skill deduplication across all canonical skills.
        Caches 384-d embeddings in memory via batch ONNX inference so conceptual synonyms
        with zero lexical overlap (e.g., 'Containerization' -> 'Docker') resolve accurately.
        """
        if not raw_name or not existing_skills:
            return None

        missing_skills = [
            s for s in existing_skills
            if s.get("id") and s.get("name") and s["id"] not in _canonical_skill_vector_cache
        ]
        if missing_skills:
            names = [s["name"].strip() for s in missing_skills]
            vecs = await self.get_embeddings_batch(names)
            for s, vec in zip(missing_skills, vecs):
                if vec:
                    _canonical_skill_vector_cache[s["id"]] = vec

        cand_vec = await self.get_embedding(raw_name.strip())
        best_skill = None
        best_sim = 0.0
        for s in existing_skills:
            s_vec = _canonical_skill_vector_cache.get(s.get("id"))
            if not s_vec:
                continue
            sim = sum(a * b for a, b in zip(cand_vec, s_vec))
            if sim > best_sim:
                best_sim = sim
                best_skill = s

        return best_skill if (best_skill and best_sim >= threshold) else None
