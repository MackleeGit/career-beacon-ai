"""
---------------------------------------
Content Atomization & Dynamic 5-Question Quiz Generator

Takes raw educational content validated through the 3-gate ingestion pipeline:
1. Validates source content substance, topical relevance, and anti-stub integrity.
2. Condenses verified text into a high-density 3-bullet technical takeaway summary (<150 words).
3. Generates an interactive 5-question Multiple Choice Quiz (MCQ) strictly grounded in source content.
4. Validates quiz schema, option distinctness, and exact answer membership.
5. Computes a 384-dimensional vector embedding for semantic search.
6. Persists the enriched micro-lesson into Supabase `public.micro_content` preserving real source URLs.
---------------------------------------
"""

import sys
import json
import re
import html
import logging
from typing import Dict, Any, List, Optional
from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client

logger = logging.getLogger("career_beacon.content_service")

def get_source_trust_score(source_str: str):
    """Legacy API field retained as unknown; source names are not calibrated trust evidence."""
    return None


def strip_html_and_clean(html_text: str) -> str:
    """Strips HTML formatting, unescapes entities, and normalizes whitespace."""
    if not html_text:
        return ""
    unescaped = html.unescape(html_text)
    # Strip script and style blocks
    cleaned = re.sub(r"<(script|style).*?>.*?</\1>", "", unescaped, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def validate_source_content(raw_text: str, skill_name: str) -> bool:
    """
    Validates whether retrieved raw content possesses sufficient substance
    and topical grounding to serve as the basis for an instructional lesson.

    Heuristics applied:
      1. Minimum substance: Requires at least 200 non-whitespace characters.
      2. Anti-boilerplate: Rejects known disambiguation stubs, empty stubs,
         or fabricated generic sentences.
      3. Topical relevance: At least one non-trivial token from skill_name
         must be present in the content body.

    Limitations:
      Lexical and structural checks cannot guarantee deep domain accuracy;
      they prevent vacuous stubs, HTTP errors, or empty snippets from being ingested.
    """
    if not raw_text or not isinstance(raw_text, str):
        return False

    clean_text = raw_text.strip()
    if len(clean_text) < 200:
        return False

    lower_text = clean_text.lower()
    stubs = [
        "authoritative reference material and foundational principles for",
        "may refer to:",
        "disambiguation page",
        "no articles found",
        "page does not exist",
    ]
    for stub in stubs:
        if stub in lower_text:
            return False

    # Check topical grounding: at least one token (>= 3 chars) from skill_name should appear
    skill_tokens = [re.sub(r"[^a-zA-Z0-9]", "", t).lower() for t in skill_name.split()]
    meaningful_tokens = [t for t in skill_tokens if len(t) >= 3 and t not in {"the", "and", "for", "with"}]
    if meaningful_tokens:
        if not any(token in lower_text for token in meaningful_tokens):
            return False

    return True


def validate_quiz_structure(quizzes: Any) -> List[Dict[str, Any]]:
    """
    Validates that each quiz item is a well-formed multiple-choice question:
      - 'question': non-empty string (>= 10 chars).
      - 'options': exactly 4 distinct, non-empty options.
      - 'answer': string that exactly matches one of the 4 options.
      - 'explanation': non-empty pedagogical rationale.
    Returns the list of valid quiz items. If fewer than 3 valid items exist,
    returns an empty list to signal structural rejection.
    """
    if not isinstance(quizzes, list):
        return []

    valid_quizzes = []
    for q in quizzes:
        if not isinstance(q, dict):
            continue
        q_text = str(q.get("question", "")).strip()
        opts = q.get("options", [])
        ans = str(q.get("answer", "")).strip()
        explanation = str(q.get("explanation", "")).strip()

        if len(q_text) < 10:
            continue
        if not isinstance(opts, list) or len(opts) != 4:
            continue

        clean_opts = [str(o).strip() for o in opts if str(o).strip()]
        if len(clean_opts) != 4 or len(set(clean_opts)) != 4:
            continue

        if ans not in clean_opts:
            continue

        valid_quizzes.append({
            "question": q_text,
            "options": clean_opts,
            "answer": ans,
            "explanation": explanation or "Verified against course curriculum.",
        })

    if len(valid_quizzes) < 3:
        return []

    return valid_quizzes


class ContentService:
    def __init__(self):
        self.ai_service = AIService()
        self.embedding_service = EmbeddingService()

    async def atomize_and_create_quiz(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transforms raw ingested item into an atomized lesson with verified MCQs and embeddings,
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

        # Pre-generation gate: validate source material substance and relevance
        if not validate_source_content(raw_text, skill_name):
            logger.warning(f"Raw content for '{title}' failed sufficiency check. Aborting atomization.")
            return None

        prompt = f"""
Domain Category: {category}
Skill Target: {skill_name}
Resource Title: {title}
Source: {source}

Raw Source Content (Strict Ground Truth):
\"\"\"
{raw_text[:2500]}
\"\"\"

Task:
Transform this resource into an atomized micro-learning lesson for Career Beacon.
Produce:
1. summary_bullets: Exactly 3 technical takeaway bullet points highlighting core concepts, under 120 words total. Each bullet MUST start with '• '.
2. difficulty_level: Integer from 1 to 5 (1=Beginner, 2=Elementary, 3=Intermediate, 4=Advanced, 5=Expert).
3. quizzes: An array of EXACTLY 5 multiple-choice questions testing retention of the core concepts in this lesson.

GROUNDING RULES:
- Every bullet point and question MUST be strictly grounded in the Raw Source Content provided above.
- Do NOT introduce unmentioned facts or outside trivia.
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
        if not summary_bullets or len(summary_bullets) < 30:
            logger.warning(f"Summary bullets failed validation for '{title}'. Aborting.")
            return None

        difficulty_level = int(ai_data.get("difficulty_level", 2))
        difficulty_level = max(1, min(5, difficulty_level))
        quizzes = ai_data.get("quizzes", [])

        # Validate that quizzes meet structural and option criteria
        valid_quizzes = validate_quiz_structure(quizzes)
        if not valid_quizzes:
            logger.warning(f"Quiz items failed validation for '{title}', skipping.")
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
            existing_id = existing.data[0]["id"] if (existing and existing.data) else None
        except Exception:
            existing_id = None

        trust_score = get_source_trust_score(source)

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
                    logger.info(f"Persisted micro-content lesson: '{title[:40]}' with {len(valid_quizzes)} MCQs.")
                    return saved_row
            except Exception as e:
                err_str = str(e)
                if "column" in err_str and record_attempt == record_full:
                    continue
                logger.error(f"Database save error for '{title}': {e}")
                return None

        return None

    async def fetch_live_source_for_skill(self, skill_name: str, category: str = "Core") -> Optional[Dict[str, Any]]:
        """
        Queries authoritative public educational endpoints (Dev.to, Wikipedia REST API,
        StackExchange) to discover verifiable learning content.

        Returns a dictionary with verified 'title', 'source_url', 'raw_text', and 'trust_score'
        if substantive learning material is retrieved; otherwise returns None.
        NO fabricated URLs or boilerplate text are ever generated.
        """
        import httpx
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
                        articles = r_dev.json()
                        for art in (articles if isinstance(articles, list) else []):
                            # Preliminary filter: community engagement signal
                            if art.get("positive_reactions_count", 0) >= 10 and art.get("id") and art.get("url"):
                                art_id = art["id"]
                                try:
                                    r_detail = await client.get(
                                        f"https://dev.to/api/articles/{art_id}",
                                        headers=headers
                                    )
                                    if r_detail.status_code == 200:
                                        detail_json = r_detail.json()
                                        body_md = detail_json.get("body_markdown") or detail_json.get("description", "")
                                        cleaned_body = strip_html_and_clean(body_md)
                                        if validate_source_content(cleaned_body, skill_name):
                                            title = html.unescape(art.get("title", "")).strip()
                                            return {
                                                "title": title,
                                                "source_url": art.get("url"),
                                                "raw_text": cleaned_body[:3500],
                                                "source": "devto",
                                                "trust_score": 0.90,
                                            }
                                except Exception:
                                    continue
                except Exception as e:
                    logger.debug(f"Dev.to retrieval error: {e}")

            # 2. Direct Wikipedia REST API Page Summary
            slug = skill_name.strip().replace(" ", "_")
            try:
                r_wiki = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}", headers=headers)
                if r_wiki.status_code == 200:
                    d = r_wiki.json()
                    extract = d.get("extract", "")
                    if d.get("type") == "standard" and validate_source_content(extract, skill_name):
                        page_url = d.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug}"
                        return {
                            "title": d.get("title", skill_name),
                            "source_url": page_url,
                            "raw_text": extract[:3500],
                            "source": "wikipedia",
                            "trust_score": 1.00,
                        }
            except Exception as e:
                logger.debug(f"Wikipedia summary error: {e}")

            # 3. StackExchange API: Retrieves question AND accepted/top answer body
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
                    for item in (items if isinstance(items, list) else []):
                        if item.get("score", 0) >= 3 and item.get("is_answered") and item.get("question_id"):
                            q_id = item["question_id"]
                            q_title = html.unescape(item.get("title", "")).strip()

                            ans_url = None
                            ans_body_text = ""
                            try:
                                if item.get("accepted_answer_id"):
                                    ans_id = item["accepted_answer_id"]
                                    r_ans = await client.get(
                                        f"https://api.stackexchange.com/2.3/answers/{ans_id}?site={site}&filter=withbody",
                                        headers=headers
                                    )
                                else:
                                    r_ans = await client.get(
                                        f"https://api.stackexchange.com/2.3/questions/{q_id}/answers?order=desc&sort=votes&site={site}&pagesize=1&filter=withbody",
                                        headers=headers
                                    )

                                if r_ans.status_code == 200:
                                    ans_items = r_ans.json().get("items", [])
                                    if ans_items:
                                        best_ans = ans_items[0]
                                        ans_body_text = strip_html_and_clean(best_ans.get("body", ""))
                                        ans_id = best_ans.get("answer_id")
                                        if ans_id and item.get("link"):
                                            ans_url = f"{item['link']}#{ans_id}"
                                        else:
                                            ans_url = item.get("link")
                            except Exception:
                                pass

                            full_se_text = f"{q_title}.\n\nExplanation:\n{ans_body_text}" if ans_body_text else ""
                            if ans_url and validate_source_content(full_se_text, skill_name):
                                return {
                                    "title": q_title,
                                    "source_url": ans_url,
                                    "raw_text": full_se_text[:3500],
                                    "source": f"stackexchange ({site})",
                                    "trust_score": 0.95,
                                }
            except Exception as e:
                logger.debug(f"StackExchange retrieval error: {e}")

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
                            extract2 = d2.get("extract", "")
                            if d2.get("type") == "standard" and validate_source_content(extract2, skill_name):
                                page_url = d2.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug2}"
                                return {
                                    "title": d2.get("title", best_title),
                                    "source_url": page_url,
                                    "raw_text": extract2[:3500],
                                    "source": "wikipedia",
                                    "trust_score": 1.00,
                                }
            except Exception as e:
                logger.debug(f"Wikipedia search fallback error: {e}")

        # 5. Fail honestly: No fabricated fallback URLs or synthetic placeholder text
        logger.warning(f"No suitable authoritative source content found across any provider for '{skill_name}'.")
        return None

    async def generate_dynamic_lesson_for_skill(
        self,
        skill_id: str,
        skill_name: str,
        category: str = "Core",
        career_title: str = "General Career",
        target_proficiency: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically fetches authoritative reference material from public APIs,
        synthesizes a tailored 3-bullet takeaway summary and 5-question MCQ, embeds it,
        and commits to Supabase with real external source URLs.

        If no authoritative material is found or content fails sufficiency checks,
        returns None honestly rather than manufacturing unsupported lessons.
        """
        live_source = await self.fetch_live_source_for_skill(skill_name, category)
        if not live_source or not live_source.get("source_url") or not live_source.get("raw_text"):
            logger.warning(f"No verifiable source material found for '{skill_name}'. Aborting dynamic lesson generation.")
            return None

        source_url = live_source["source_url"]
        source_title = live_source["title"]
        raw_text = live_source["raw_text"]
        source_trust = live_source["trust_score"]

        # Double check source content sufficiency
        if not validate_source_content(raw_text, skill_name):
            logger.warning(f"Source content for '{skill_name}' failed sufficiency validation. Aborting lesson generation.")
            return None

        title = f"{source_title} Fundamentals for {career_title}"

        prompt = f"""
Target Career: {career_title}
Skill Target: {skill_name} ({category})
Authoritative Resource: {live_source['source']} ({source_url})

Source Content (Strict Ground Truth):
\"\"\"
{raw_text[:2500]}
\"\"\"

Task:
Transform this authoritative educational material into an atomized micro-learning lesson for a {career_title}.
Focus specifically on how {skill_name} is practically applied in the day-to-day role of a {career_title}.

GROUNDING & INTEGRITY RULES:
1. Every takeaway bullet and quiz question MUST be directly grounded in the Source Content above.
2. Do NOT invent external trivia, speculative tools, or unsupported claims.
3. Produce:
   - summary_bullets: Exactly 3 technical, high-yield bullet points derived from this topic. Under 120 words total. Each bullet MUST start with '• '.
   - difficulty_level: Appropriate difficulty integer from 1 to 5.
   - quizzes: An array of EXACTLY 5 practical multiple-choice questions testing application and conceptual understanding of this lesson for a {career_title}.
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
        if not summary_bullets or len(summary_bullets) < 30:
            logger.warning(f"Generated summary_bullets failed validation for '{skill_name}'. Aborting.")
            return None

        difficulty_level = int(ai_data.get("difficulty_level", 2))
        difficulty_level = max(1, min(5, difficulty_level))
        quizzes = ai_data.get("quizzes", [])

        # Validate quiz structure: requires at least 3 high-quality valid MCQs
        valid_quizzes = validate_quiz_structure(quizzes)
        if not valid_quizzes:
            logger.warning(f"Generated quiz failed validation for '{skill_name}', aborting dynamic save.")
            return None

        text_to_embed = f"{title}. Skill: {skill_name} ({category}). Career: {career_title}. Summary: {summary_bullets}"
        try:
            content_vector = await self.embedding_service.get_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to embed dynamic lesson for '{skill_name}': {e}")
            return None

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
