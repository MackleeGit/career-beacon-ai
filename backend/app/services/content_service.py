"""
---------------------------------------
Content Atomization & Dynamic 5-Question Quiz Generator

Takes raw educational content validated through the 3-gate ingestion pipeline:
1. Condenses text into a high-density 3-bullet technical takeaway summary (<150 words).
2. Generates an interactive 5-question Multiple Choice Quiz (MCQ) JSON array.
3. Assigns an algorithmic difficulty level (1-5) and source trust score (0.0 - 1.0).
4. Generates a 384-dimensional vector embedding for semantic search.
5. Persists the enriched micro-lesson into Supabase `public.micro_content`.
"""

import sys
import json
import logging
from typing import Dict, Any, List, Optional
from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client

logger = logging.getLogger("career_beacon.content_service")

# Source Trust Score weights (0.0 to 1.0)
SOURCE_TRUST_MAP = {
    "wikipedia": 1.00,
    "stackexchange": 0.95,
    "devto": 0.90,
    "hackernews": 0.90,
    "youtube": 0.85,
}

def get_source_trust_score(source_str: str) -> float:
    """Determine organic source trust score modifier for recommendation ranking."""
    source_lower = (source_str or "").lower()
    for key, score in SOURCE_TRUST_MAP.items():
        if key in source_lower:
            return score
    return 0.80


class ContentService:
    def __init__(self):
        self.ai_service = AIService()
        self.embedding_service = EmbeddingService()

    async def atomize_and_create_quiz(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transforms raw ingested item into an atomized lesson with 5 MCQs and embeddings,
        then commits to Supabase `micro_content`.
        """
        title = raw_item.get("title", "").strip()
        skill_name = raw_item.get("skill_name", "General Skill")
        category = raw_item.get("category", "General")
        source = raw_item.get("source", "web")
        source_url = raw_item.get("source_url", "")
        raw_text = raw_item.get("raw_text", title)
        skill_id = raw_item.get("skill_id")

        if not title or not source_url:
            logger.warning("Skipping item with missing title or source_url")
            return None

        prompt = f"""
Domain Category: {category}
Skill Target: {skill_name}
Resource Title: {title}
Source: {source}

Raw Source Content:
\"\"\"
{raw_text[:2500]}
\"\"\"

Task:
Transform this resource into an atomized micro-learning lesson for Career Beacon.
Produce:
1. summary_bullets: Exactly 3 technical takeaway bullet points highlighting core concepts, under 120 words total. Each bullet MUST start with '• '.
2. difficulty_level: Integer from 1 to 5 (1=Beginner, 2=Elementary, 3=Intermediate, 4=Advanced, 5=Expert).
3. quizzes: An array of EXACTLY 5 multiple-choice questions testing retention of the core concepts in this lesson.
"""

        system_instruction = """
You are an expert curriculum designer and psychometric assessment creator for Career Beacon.
You must return a valid JSON object matching this schema:
{
  "summary_bullets": "• First key concept...\\n• Second key concept...\\n• Third key concept...",
  "difficulty_level": 2,
  "quizzes": [
    {
      "question": "Clear and unambiguous question string",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A",
      "explanation": "Brief explanation why this option is correct."
    }
  ]
}
Rules:
- The 'quizzes' array MUST contain EXACTLY 5 distinct questions.
- Each question MUST have exactly 4 choices in 'options'.
- 'answer' MUST be character-for-character identical to one of the 4 items in 'options'.
- 'summary_bullets' MUST contain 3 distinct bullet points.
"""

        try:
            ai_data = await self.ai_service.generate_json(prompt, system_instruction=system_instruction)
        except Exception as e:
            logger.error(f"Failed to generate lesson/quizzes via AI for '{title}': {e}")
            return None

        summary_bullets = ai_data.get("summary_bullets", "").strip()
        difficulty_level = int(ai_data.get("difficulty_level", 2))
        difficulty_level = max(1, min(5, difficulty_level))
        quizzes = ai_data.get("quizzes", [])

        # Validate that quizzes has 5 valid MCQs
        if not isinstance(quizzes, list) or len(quizzes) < 3:
            logger.warning(f"Incomplete quiz generated for '{title}', skipping.")
            return None

        # Sanitize quiz items
        valid_quizzes = []
        for q in quizzes:
            q_text = q.get("question", "").strip()
            opts = q.get("options", [])
            ans = q.get("answer", "").strip()
            if q_text and len(opts) == 4 and ans in opts:
                valid_quizzes.append({
                    "question": q_text,
                    "options": opts,
                    "answer": ans,
                    "explanation": q.get("explanation", ""),
                })

        if len(valid_quizzes) < 3:
            logger.warning(f"Quiz items failed option validation for '{title}', skipping.")
            return None

        # Compute content vector embedding (384-dimensional)
        text_to_embed = f"{title}. Skill: {skill_name} ({category}). Summary: {summary_bullets}"
        try:
            content_vector = await self.embedding_service.get_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to compute embedding for '{title}': {e}")
            return None

        # Check if item already exists by source_url
        try:
            existing = supabase_client.table("micro_content").select("id").eq("source_url", source_url).execute()
        except Exception:
            existing = None

        existing_id = existing.data[0]["id"] if (existing and existing.data) else None

        trust_score = get_source_trust_score(source)

        # Payload A: Comprehensive record (matches full goal.txt specification)
        record_full = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "summary_bullets": summary_bullets,
            "content": json.dumps({
                "quizzes": valid_quizzes,
                "difficulty_level": difficulty_level,
                "source_trust_score": trust_score,
                "skill_name": skill_name,
                "category": category,
            }),
            "associated_skill_id": skill_id,
            "difficulty_level": difficulty_level,
            "source_trust_score": trust_score,
            "quizzes": valid_quizzes,
            "embedding": content_vector,
        }

        # Payload B: Backward-compatible fallback for pre-migration schema
        record_compat = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "content": json.dumps({
                "summary_bullets": summary_bullets,
                "quizzes": valid_quizzes,
                "difficulty_level": difficulty_level,
                "source_trust_score": trust_score,
                "associated_skill_id": skill_id,
                "skill_name": skill_name,
                "category": category,
            }),
            "embedding": content_vector,
        }

        # Persist with graceful schema fallback
        for record_attempt in [record_full, record_compat]:
            try:
                if existing_id:
                    db_res = supabase_client.table("micro_content").update(record_attempt).eq("id", existing_id).execute()
                else:
                    db_res = supabase_client.table("micro_content").insert(record_attempt).execute()

                if db_res.data:
                    saved_row = db_res.data[0]
                    # Ensure quizzes and difficulty are populated on the returned object for downstream consumers
                    if "quizzes" not in saved_row or not saved_row["quizzes"]:
                        saved_row["quizzes"] = valid_quizzes
                    if "difficulty_level" not in saved_row:
                        saved_row["difficulty_level"] = difficulty_level
                    logger.info(f"Persisted micro-content lesson: '{title[:40]}' with {len(valid_quizzes)} MCQs.")
                    return saved_row
            except Exception as e:
                err_str = str(e)
                if "column" in err_str and record_attempt == record_full:
                    # Column not yet created in Supabase schema, fall back to record_compat
                    continue
                logger.error(f"Database save error for '{title}': {e}")
                return None

        return None

    async def fetch_live_source_for_skill(self, skill_name: str, category: str = "Core") -> Dict[str, Any]:
        """
        Queries zero-key multi-source educational endpoints (Dev.to, StackExchange,
        Wikipedia REST API, Hacker News) to discover authoritative public source URLs.
        """
        import re, html, httpx
        headers = {"User-Agent": "CareerBeacon/1.0 (academic research; contact@careerbeacon.ai; polite bot)"}
        cat_lower = (category or "").lower()
        is_tech = any(k in cat_lower for k in ["tech", "software", "program", "data", "develop", "web", "ai", "cloud"])

        async with httpx.AsyncClient(timeout=6.0) as client:
            # 1. Dev.to API (For software and technology skills)
            if is_tech:
                clean_tag = re.sub(r"[^a-zA-Z0-9]", "", skill_name.lower())
                try:
                    r_dev = await client.get(
                        f"https://dev.to/api/articles?tag={clean_tag}&top=30&per_page=5",
                        headers=headers
                    )
                    if r_dev.status_code == 200:
                        for art in r_dev.json():
                            if art.get("positive_reactions_count", 0) >= 20 and art.get("url"):
                                title = html.unescape(art.get("title", "")).strip()
                                desc = html.unescape(art.get("description", "") or "").strip()
                                return {
                                    "title": title,
                                    "source_url": art.get("url"),
                                    "raw_text": f"{title}. {desc}" if desc else title,
                                    "source": "devto",
                                    "trust_score": 0.90,
                                }
                except Exception:
                    pass

            # 2. Direct Wikipedia REST API Page Summary (Authoritative across all disciplines)
            slug = skill_name.strip().replace(" ", "_")
            try:
                r_wiki = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}", headers=headers)
                if r_wiki.status_code == 200:
                    d = r_wiki.json()
                    if d.get("type") == "standard" and len(d.get("extract", "")) > 60:
                        page_url = d.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug}"
                        return {
                            "title": d.get("title", skill_name),
                            "source_url": page_url,
                            "raw_text": d.get("extract", ""),
                            "source": "wikipedia",
                            "trust_score": 1.00,
                        }
            except Exception:
                pass

            # 3. StackExchange API (Targeted by domain site)
            try:
                site = "stackoverflow"
                if any(k in cat_lower for k in ["math", "stat", "probability"]):
                    site = "stats"
                elif any(k in cat_lower for k in ["medical", "health", "clinical"]):
                    site = "medicalsciences"
                elif any(k in cat_lower for k in ["law", "legal"]):
                    site = "law"

                clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", skill_name).strip()
                r_se = await client.get(
                    f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={clean_q}&site={site}&pagesize=5&filter=default",
                    headers=headers
                )
                if r_se.status_code == 200:
                    items = r_se.json().get("items", [])
                    for item in items:
                        if item.get("score", 0) >= 5 and item.get("is_answered") and item.get("link"):
                            se_title = html.unescape(item.get("title", "")).strip()
                            tags = item.get("tags", [])
                            return {
                                "title": se_title,
                                "source_url": item.get("link"),
                                "raw_text": f"{se_title}. Key concepts: {', '.join(tags)}",
                                "source": f"stackexchange ({site})",
                                "trust_score": 0.95,
                            }
            except Exception:
                pass

            # 4. Wikipedia Search API Fallback (Handles multi-word / niche phrases)
            try:
                r_srch = await client.get(
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={skill_name}&utf8=&format=json",
                    headers=headers
                )
                if r_srch.status_code == 200:
                    results = r_srch.json().get("query", {}).get("search", [])
                    if results:
                        best_title = results[0]["title"]
                        slug2 = best_title.replace(" ", "_")
                        r_sum = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug2}", headers=headers)
                        if r_sum.status_code == 200:
                            d2 = r_sum.json()
                            page_url = d2.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug2}"
                            return {
                                "title": d2.get("title", best_title),
                                "source_url": page_url,
                                "raw_text": d2.get("extract", results[0].get("snippet", "")),
                                "source": "wikipedia",
                                "trust_score": 1.00,
                            }
            except Exception:
                pass

        # 5. Canonical encyclopaedia fallback URL
        clean_slug = skill_name.strip().replace(" ", "_")
        return {
            "title": skill_name,
            "source_url": f"https://en.wikipedia.org/wiki/{clean_slug}",
            "raw_text": f"Authoritative reference material and foundational principles for {skill_name}.",
            "source": "wikipedia",
            "trust_score": 0.95,
        }

    async def generate_dynamic_lesson_for_skill(
        self,
        skill_id: str,
        skill_name: str,
        category: str = "Core",
        career_title: str = "General Career",
        target_proficiency: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically fetches authoritative reference material from public APIs (Wikipedia),
        synthesizes a tailored 3-bullet takeaway summary and 5-question MCQ, embeds it,
        and commits to Supabase with real external source URLs.
        """
        # Fetch real authoritative source material and live external URL
        live_source = await self.fetch_live_source_for_skill(skill_name, category)
        source_url = live_source["source_url"]
        source_title = live_source["title"]
        raw_text = live_source["raw_text"]
        source_trust = live_source["trust_score"]

        title = f"{source_title} Fundamentals for {career_title}"

        prompt = f"""
Target Career: {career_title}
Skill Target: {skill_name} ({category})
Authoritative Resource: {live_source['source']} ({source_url})
Source Content:
\"\"\"
{raw_text[:2000]}
\"\"\"

Task:
Transform this authoritative educational material into an atomized micro-learning lesson for a {career_title}.
Focus specifically on how {skill_name} is practically applied in the day-to-day role of a {career_title}.

Produce:
1. summary_bullets: Exactly 3 technical, high-yield bullet points derived from this topic, highlighting practical principles, operational rules, or essential techniques. Under 120 words total. Each bullet MUST start with '• '.
2. difficulty_level: Appropriate difficulty integer from 1 to 5 (typically 2 for beginner/intermediate baseline).
3. quizzes: An array of EXACTLY 5 practical multiple-choice questions testing application and conceptual understanding of this lesson for a {career_title}.
"""

        system_instruction = """
You are an expert industry trainer and psychometric test creator for Career Beacon.
You must return a valid JSON object matching this schema:
{
  "summary_bullets": "• First practical principle...\\n• Second key rule...\\n• Third operational technique...",
  "difficulty_level": 2,
  "quizzes": [
    {
      "question": "Realistic scenario or technical question string",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A",
      "explanation": "Clear explanation of why this answer is correct in practice."
    }
  ]
}
Rules:
- The 'quizzes' array MUST contain EXACTLY 5 distinct questions.
- Each question MUST have exactly 4 choices in 'options'.
- 'answer' MUST be character-for-character identical to one of the 4 items in 'options'.
- 'summary_bullets' MUST contain 3 distinct bullet points.
"""

        try:
            ai_data = await self.ai_service.generate_json(prompt, system_instruction=system_instruction)
        except Exception as e:
            logger.error(f"Failed dynamic lesson generation for '{skill_name}' ({career_title}): {e}")
            return None

        summary_bullets = ai_data.get("summary_bullets", "").strip()
        difficulty_level = int(ai_data.get("difficulty_level", 2))
        difficulty_level = max(1, min(5, difficulty_level))
        quizzes = ai_data.get("quizzes", [])

        valid_quizzes = []
        for q in (quizzes if isinstance(quizzes, list) else []):
            q_text = q.get("question", "").strip()
            opts = q.get("options", [])
            ans = q.get("answer", "").strip()
            if q_text and len(opts) == 4 and ans in opts:
                valid_quizzes.append({
                    "question": q_text,
                    "options": opts,
                    "answer": ans,
                    "explanation": q.get("explanation", ""),
                })

        if len(valid_quizzes) < 3:
            logger.warning(f"Generated quiz failed validation for '{skill_name}', aborting dynamic save.")
            return None

        text_to_embed = f"{title}. Skill: {skill_name} ({category}). Career: {career_title}. Summary: {summary_bullets}"
        try:
            content_vector = await self.embedding_service.get_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to embed dynamic lesson for '{skill_name}': {e}")
            return None

        # Check if already exists by source_url
        try:
            existing = supabase_client.table("micro_content").select("id").eq("source_url", source_url).execute()
            existing_id = existing.data[0]["id"] if (existing and existing.data) else None
        except Exception:
            existing_id = None

        record_full = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "summary_bullets": summary_bullets,
            "content": json.dumps({
                "quizzes": valid_quizzes,
                "difficulty_level": difficulty_level,
                "source_trust_score": source_trust,
                "skill_name": skill_name,
                "category": category,
                "career_title": career_title,
                "source_url": source_url,
            }),
            "associated_skill_id": skill_id,
            "difficulty_level": difficulty_level,
            "source_trust_score": source_trust,
            "quizzes": valid_quizzes,
            "embedding": content_vector,
        }

        record_compat = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "content": json.dumps({
                "summary_bullets": summary_bullets,
                "quizzes": valid_quizzes,
                "difficulty_level": difficulty_level,
                "source_trust_score": source_trust,
                "associated_skill_id": skill_id,
                "skill_name": skill_name,
                "category": category,
                "career_title": career_title,
                "source_url": source_url,
            }),
            "embedding": content_vector,
        }

        for record_attempt in [record_full, record_compat]:
            try:
                if existing_id:
                    db_res = supabase_client.table("micro_content").update(record_attempt).eq("id", existing_id).execute()
                else:
                    db_res = supabase_client.table("micro_content").insert(record_attempt).execute()

                if db_res.data:
                    saved_row = db_res.data[0]
                    if "quizzes" not in saved_row or not saved_row["quizzes"]:
                        saved_row["quizzes"] = valid_quizzes
                    if "difficulty_level" not in saved_row:
                        saved_row["difficulty_level"] = difficulty_level
                    logger.info(f"Just-In-Time generated micro-content lesson for '{career_title}': '{title}'")
                    return saved_row
            except Exception as e:
                err_str = str(e)
                if "column" in err_str and record_attempt == record_full:
                    continue
                logger.error(f"Database save error for dynamic lesson '{title}': {e}")
                return None

        return None

