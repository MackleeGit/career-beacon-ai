"""
Modular Content Ingestion Adapter Registry
------------------------------------------
Exposes each instructional source adapter individually for isolated testing,
debugging, and field-aware orchestration.
"""

from typing import Dict, Any, Optional, List
import httpx
from app.services.content_service import (
    ContentService,
    SOURCE_AUTHORITY_WEIGHTS,
    ADAPTER_DISPLAY_LABELS,
    classify_source_adapter,
    validate_source_content,
    hydrate_micro_content_row,
)

ADAPTER_NAMES: List[str] = [
    "youtube",
    "mdn",
    "structured_tutorial",
    "open_textbook",
    "clinical_science",
    "arxiv",
    "ecfr",
    "owasp",
    "osha",
    "finance",
    "openalex",
    "wikipedia",
]


async def test_single_adapter(
    adapter_name: str,
    skill_name: str,
    career_title: str = "",
    category: str = "Core",
    field_id: str = "tech",
    excluded: Optional[set] = None,
) -> Optional[Dict[str, Any]]:
    """
    Runs a single named instructional adapter in isolation for debugging and verification.
    """
    svc = ContentService()
    excl = excluded or set()
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        dispatch = {
            "youtube": lambda: svc._fetch_youtube_lecture(client, skill_name, career_title, excl, field_id=field_id),
            "mdn": lambda: svc._fetch_mdn_docs(client, skill_name, category, career_title, excl),
            "structured_tutorial": lambda: svc._fetch_structured_tutorial(client, skill_name, category, excl, career_title=career_title),
            "open_textbook": lambda: svc._fetch_open_textbook(client, skill_name, career_title, excl),
            "clinical_science": lambda: svc._fetch_clinical_and_science(client, skill_name, career_title, excl),
            "arxiv": lambda: svc._fetch_arxiv_technical(client, skill_name, career_title, excl),
            "ecfr": lambda: svc._fetch_ecfr_regulations(client, skill_name, career_title, excl),
            "owasp": lambda: svc._fetch_owasp_cheatsheet(client, skill_name, career_title, excl),
            "osha": lambda: svc._fetch_osha_standards(client, skill_name, career_title, excl),
            "finance": lambda: svc._fetch_finance_knowledge(client, skill_name, career_title, excl),
            "openalex": lambda: svc._fetch_openalex_chapter(client, skill_name, career_title, excl),
            "wikipedia": lambda: svc._fetch_wikipedia_fallback(client, skill_name, excl, career_title=career_title),
        }
        fn = dispatch.get(adapter_name)
        if not fn:
            raise ValueError(f"Unknown adapter '{adapter_name}'. Valid adapters: {ADAPTER_NAMES}")
        return await fn()

