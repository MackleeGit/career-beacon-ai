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

