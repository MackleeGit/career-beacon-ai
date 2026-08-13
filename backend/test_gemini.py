from app.services.gemini_service import GeminiService
import asyncio

async def main():
    service = GeminiService()
    try:
        data = await service.generate_json('{"message": "Say hello world and return it in JSON format {"hello": "world"}"}', None)
        print(f"Gemini output: {data}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
