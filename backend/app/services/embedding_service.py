from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        # The PDF specifically mentions using the all-MiniLM-L6-v2 model 
        # which natively outputs 384-dimensional dense vectors.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generates a 384-dimensional vector embedding for the input text.
        """
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")
            
        # sentence-transformers encode method returns a numpy array. 
        # We convert it to a flat python list of floats for Supabase pgvector.
        embedding = self.model.encode(text)
        return embedding.tolist()
