from fastembed import TextEmbedding

class EmbeddingService:
    def __init__(self):
        # The PDF specifically mentions using the all-MiniLM-L6-v2 model 
        # which natively outputs 384-dimensional dense vectors.
        # We use FastEmbed instead of sentence-transformers to avoid PyTorch OOMs on 512MB RAM tiers.
        self.model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    async def get_embedding(self, text: str) -> list[float]:
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
