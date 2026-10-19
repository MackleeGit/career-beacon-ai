from typing import Optional, List
from fastembed import TextEmbedding

# Module-level shared singleton to ensure only ONE ONNX model instance is loaded in RAM
_shared_model: Optional[TextEmbedding] = None

def _get_model() -> TextEmbedding:
    global _shared_model
    if _shared_model is None:
        # Lazy-load all-MiniLM-L6-v2 on first inference request to keep boot RAM minimal (<100MB)
        _shared_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _shared_model

class EmbeddingService:
    def __init__(self):
        # Lightweight wrapper; model is loaded on-demand via singleton
        pass

    @property
    def model(self) -> TextEmbedding:
        return _get_model()

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional vector embedding for the input text.
        """
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")
            
        # fastembed returns a generator of numpy arrays. 
        # We convert it to a flat python list of floats for Supabase pgvector.
        embedding_generator = self.model.embed([text])
        embedding = list(embedding_generator)[0]
        return embedding.tolist()
