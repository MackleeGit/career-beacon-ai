from app.services.embedding_service import EmbeddingService
import asyncio

async def main():
    service = EmbeddingService()
    embedding = await service.get_embedding("Test career")
    print(f'Dimension: {len(embedding)}')

asyncio.run(main())
