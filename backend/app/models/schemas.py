from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimensions: int

class GenerationRequest(BaseModel):
    prompt: str
    system_instruction: Optional[str] = None

class GenerationResponse(BaseModel):
    data: Dict[str, Any]
