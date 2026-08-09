import httpx
import json
from app.core.config import settings

class GeminiService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generates a 1536-dimensional vector embedding for the input text using Matryoshka Representation Learning.
        """
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY is not configured correctly.")

        url = f"{self.base_url}/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "content": {
                "parts": [{"text": text}]
            },
            "embedContentConfig": {
                "outputDimensionality": 1536
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=15.0)
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Gemini Embedding API Error: {response.status_code} {response.text}",
                    request=response.request,
                    response=response
                )
            data = response.json()
            return data["embedding"]["values"]

    async def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        """
        Generates structured JSON content using gemini-2.5-flash.
        """
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY is not configured correctly.")

        url = f"{self.base_url}/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Gemini Generation API Error: {response.status_code} {response.text}",
                    request=response.request,
                    response=response
                )
            data = response.json()
            try:
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_content)
            except (KeyError, IndexError, ValueError) as e:
                raise ValueError(f"Failed to parse JSON response from Gemini API: {e}. Raw response: {data}")
