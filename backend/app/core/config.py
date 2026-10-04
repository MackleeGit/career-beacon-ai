import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gemini_api_key: str = "your_gemini_api_key_here"
    groq_api_key: str = "your_groq_api_key_here"  # Get free key at console.groq.com

    model_config = SettingsConfigDict(
        # Load from .env or backend/.env depending on cwd context
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
