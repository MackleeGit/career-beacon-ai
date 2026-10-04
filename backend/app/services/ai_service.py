"""
ai_service.py
-------------
Multi-provider AI service with automatic fallback.

Priority:
  1. Groq  – openai/gpt-oss-120b      (free, fast, reliable)
  2. Gemini – gemini-2.5-flash         (free, Google, backup)

Each provider gets MAX_RETRIES attempts with exponential backoff on
transient errors (429, 503) before the next provider is tried.
"""

import json
import asyncio
import httpx
from app.core.config import settings

MAX_RETRIES = 3
BASE_DELAY = 1.5   # seconds; doubles each retry

# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

async def _call_groq(prompt: str, system_instruction: str, client: httpx.AsyncClient) -> dict:
    """Call Groq's OpenAI-compatible chat completions endpoint."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-oss-120b",
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        },
        timeout=30.0,
    )
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"Groq API error {response.status_code}: {response.text}",
            request=response.request,
            response=response,
        )
    data = response.json()
    return json.loads(data["choices"][0]["message"]["content"])


async def _call_gemini(prompt: str, system_instruction: str, client: httpx.AsyncClient) -> dict:
    """Call the Gemini REST API (v1, not v1beta — more stable model support)."""
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    response = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={settings.gemini_api_key}",
        json=payload,
        timeout=30.0,
    )
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"Gemini API error {response.status_code}: {response.text}",
            request=response.request,
            response=response,
        )
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

TRANSIENT_CODES = {429, 503}

async def _with_retries(provider_fn, label: str, **kwargs) -> dict:
    """Run a provider function with exponential-backoff retries on transient errors."""
    delay = BASE_DELAY
    last_err = None
    async with httpx.AsyncClient() as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[AI] {label} – attempt {attempt}/{MAX_RETRIES}")
                return await provider_fn(client=client, **kwargs)
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in TRANSIENT_CODES and attempt < MAX_RETRIES:
                    print(f"[AI] {label} transient error ({e.response.status_code}), retrying in {delay}s…")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    # Non-retriable (400, 404, auth errors) or out of retries
                    print(f"[AI] {label} failed: {e}")
                    break
            except Exception as e:
                last_err = e
                print(f"[AI] {label} unexpected error: {e}")
                break
    raise last_err


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class AIService:
    """
    Drop-in replacement for GeminiService.
    Usage: await ai_service.generate_json(prompt, system_instruction=...)
    """

    def __init__(self):
        self._providers = []
        # Only register providers whose keys are configured
        if settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here":
            self._providers.append(("Groq/gpt-oss-120b", _call_groq))
        if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
            self._providers.append(("Gemini/gemini-2.5-flash", _call_gemini))
        if not self._providers:
            raise RuntimeError("No AI providers configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env")

    async def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        """
        Generate a JSON response using the best available provider.
        Falls through providers in order on sustained failures.
        """
        last_err = None
        for label, fn in self._providers:
            try:
                return await _with_retries(fn, label, prompt=prompt, system_instruction=system_instruction)
            except Exception as e:
                last_err = e
                print(f"[AI] {label} exhausted, trying next provider…")
                continue

        raise RuntimeError(
            f"All AI providers failed. Last error: {last_err}"
        )
