from fastapi import APIRouter, HTTPException
from app.models.schemas import EmbeddingRequest, EmbeddingResponse, GenerationRequest, GenerationResponse
from app.services.gemini_service import GeminiService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client

router = APIRouter(prefix="/api/test", tags=["Verification / Verification Endpoints"])
gemini_service = GeminiService()
embedding_service = EmbeddingService()

@router.post("/minilm-embedding", response_model=EmbeddingResponse)
async def test_minilm_embedding(request: EmbeddingRequest):
    try:
        embedding = await embedding_service.get_embedding(request.text)
        return EmbeddingResponse(embedding=embedding, dimensions=len(embedding))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")

@router.post("/gemini-generate", response_model=GenerationResponse)
async def test_gemini_generate(request: GenerationRequest):
    try:
        data = await gemini_service.generate_json(request.prompt, request.system_instruction)
        return GenerationResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate JSON content: {str(e)}")

@router.get("/supabase")
async def test_supabase_connection():
    try:
        # Fetch pre-seeded careers to verify read capabilities
        response = supabase_client.table("careers").select("*").execute()
        return {
            "status": "connected",
            "table": "careers",
            "record_count": len(response.data),
            "records": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase Database Connection Failed: {str(e)}")
