"""
ai_service.py
-------------
Multi-provider AI service with automatic fallback.

Priority:
  1. Groq - openai/gpt-oss-120b (fast, reliable)
  2. Gemini - gemini-2.0-flash (backup)

Each provider gets MAX_RETRIES attempts with exponential backoff on
transient errors (429, 503, 500) or malformed JSON before the next provider is tried.
"""

import json
import re
import asyncio
import httpx
from app.core.config import settings

MAX_RETRIES = 3
BASE_DELAY = 1.2   # seconds; doubles each retry


def _parse_json_Clean(raw_text: str) -> dict:
    """Robustly parse JSON even if the LLM wraps it in markdown fences or prose."""
    if not raw_text:
        raise ValueError("Empty response from AI provider.")
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Extract first {...} object block if present
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group(0))
        raise


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

async def _call_groq(prompt: str, system_instruction: str, client: httpx.AsyncClient) -> dict:
    """Call Groq's OpenAI-compatible chat completions endpoint."""
    messages = []
    sys_content = system_instruction or "Respond strictly in JSON format."
    if "json" not in sys_content.lower():
        sys_content += " Respond in JSON format."
    messages.append({"role": "system", "content": sys_content})
    user_content = prompt if "json" in prompt.lower() else prompt + " (Format response as JSON)"
    messages.append({"role": "user", "content": user_content})

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
            "temperature": 0.3,
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
    return _parse_json_Clean(data["choices"][0]["message"]["content"])


async def _call_gemini(prompt: str, system_instruction: str, client: httpx.AsyncClient) -> dict:
    """Call the Gemini REST API."""
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    for model_name in ("gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            f"?key={settings.gemini_api_key}",
            json=payload,
            timeout=30.0,
        )
        if response.status_code == 404:
            continue
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Gemini API error {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_Clean(text)

    raise httpx.HTTPStatusError(
        f"Gemini API error {response.status_code}: {response.text}",
        request=response.request,
        response=response,
    )


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

TRANSIENT_CODES = {400, 429, 500, 502, 503, 504}

async def _with_retries(provider_fn, label: str, **kwargs) -> dict:
    """Run a provider function with exponential-backoff retries on transient or JSON errors."""
    delay = BASE_DELAY
    last_err = None
    async with httpx.AsyncClient() as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[AI] {label} - attempt {attempt}/{MAX_RETRIES}")
                return await provider_fn(client=client, **kwargs)
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in TRANSIENT_CODES and attempt < MAX_RETRIES:
                    print(f"[AI] {label} status {e.response.status_code}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    print(f"[AI] {label} failed: {e}")
                    break
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_err = e
                if attempt < MAX_RETRIES:
                    print(f"[AI] {label} parse error ({e}), retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
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
    Service for structured JSON generation with multi-provider fallback.
    Usage: await ai_service.generate_json(prompt, system_instruction=...)
    """

    def __init__(self):
        self._providers = []
        if settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here":
            self._providers.append(("Groq/gpt-oss-120b", _call_groq))
        if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
            self._providers.append(("Gemini/gemini-2.0-flash", _call_gemini))
        if not self._providers:
            raise RuntimeError("No AI providers configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env")

    async def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        last_err = None
        for label, fn in self._providers:
            try:
                return await _with_retries(fn, label, prompt=prompt, system_instruction=system_instruction)
            except Exception as e:
                last_err = e
                print(f"[AI] {label} exhausted, trying next provider...")
                continue

        raise RuntimeError(
            f"All AI providers failed. Last error: {last_err}"
        )
