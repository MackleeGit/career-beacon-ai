import pytest
import math
from app.services.embedding_service import EmbeddingService

@pytest.mark.asyncio
async def test_embedding_dimensions_and_normalization():
    svc = EmbeddingService()
    vec = await svc.get_embedding("Software Developer")
    
    assert isinstance(vec, list), "Embedding should be a list"
    assert len(vec) == 384, f"Expected 384 dimensions, got {len(vec)}"
    
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4, f"Expected unit normalized vector, got L2 norm {norm}"

@pytest.mark.asyncio
async def test_embedding_empty_text_rejection():
    svc = EmbeddingService()
    with pytest.raises(ValueError, match="cannot be empty"):
        await svc.get_embedding("   ")
