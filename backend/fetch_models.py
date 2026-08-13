import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

async def get_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        models = data.get("models", [])
        for m in models:
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                print(m["name"])

asyncio.run(get_models())
