"""
---------------------------------------
Modular Instructional Content Engine & Self-Contained 5-Question Quiz Generator (v2)

Architecture:
1. 7 Pluggable Instructional Source Adapters (Zero hardcoded career hacks, zero anecdotal Q&A forums):
   - Adapter 1: YouTubeLectureAdapter (YouTube Educational Tutorials + Transcript Extraction)
   - Adapter 2: StructuredTutorialAdapter (GeeksforGeeks, Tutorialspoint, W3Schools)
   - Adapter 3: OpenTextbookAdapter (Wikibooks & Wikiversity Courseware via MediaWiki API)
   - Adapter 4: ClinicalScienceAdapter (NCBI Bookshelf / StatPearls & Europe PMC REST API)
   - Adapter 5: MDNDocsAdapter (MDN Web Docs Search API for Software/Web/Cloud/Data)
   - Adapter 6: OpenAlexAdapter (OpenAlex Open-Access Textbook Chapters & Review Articles)
   - Adapter 7: WikipediaFallbackAdapter (Multi-section extracts, strictly last-resort & capped by Mixer)
2. 3-Gate Ingestion Filter:
   - Gate 1: Lexical anti-anecdote / anti-stub check + source authority floor.
   - Gate 2: Substance (>= 200 chars) & topical keyword grounding.
   - Gate 3: Self-contained LLM synthesis producing:
       * concept_overview (150-220 word structured mini-lesson)
       * practice_scenario (real-world occupational application for target career)
       * summary_bullets (3 high-yield takeaways)
       * quizzes (5 applied MCQs strictly answerable from the in-app lesson)
---------------------------------------
"""

import asyncio
import json
import re
import html
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus, urlparse
import httpx

from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client
from app.core.config import settings
from app.core.career_fields import CAREER_FIELDS, classify_career_field

logger = logging.getLogger("career_beacon.content_service")

# Calibrated base authority weights by instructional adapter
SOURCE_AUTHORITY_WEIGHTS: Dict[str, float] = {
    "owasp": 0.96,
    "osha": 0.97,
    "ecfr": 0.97,
    "finance": 0.93,
    "youtube": 0.94,
    "structured_tutorial": 0.92,
    "open_textbook": 0.90,
    "clinical_science": 0.95,
    "mdn": 0.95,
    "arxiv": 0.91,
    "openalex": 0.86,
    "wikipedia": 0.60,
}

ACADEMIC_USER_AGENT = "CareerBeacon/2.0 (Academic Career Mentorship Engine; mailto:research@careerbeacon.ai)"
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def get_source_trust_score(source_str: str) -> Optional[float]:
    """Return calibrated base authority score for known instructional adapters."""
    if not source_str:
        return None
    low = source_str.lower()
    if "owasp" in low:
        return SOURCE_AUTHORITY_WEIGHTS["owasp"]
    if "ecfr" in low or "federal regulation" in low or "cfr" in low:
        return SOURCE_AUTHORITY_WEIGHTS["ecfr"]
    if "osha" in low or "safety standard" in low or "niosh" in low:
        return SOURCE_AUTHORITY_WEIGHTS["osha"]
    if "finance" in low or "accounting standard" in low:
        return SOURCE_AUTHORITY_WEIGHTS["finance"]
    if "youtube" in low:
        return SOURCE_AUTHORITY_WEIGHTS["youtube"]
    if any(k in low for k in ("geeksforgeeks", "tutorialspoint", "w3schools", "structured_tutorial")):
        return SOURCE_AUTHORITY_WEIGHTS["structured_tutorial"]
    if any(k in low for k in ("wikibooks", "wikiversity", "open_textbook", "openstax", "libretexts")):
        return SOURCE_AUTHORITY_WEIGHTS["open_textbook"]
    if any(k in low for k in ("ncbi", "statpearls", "europe pmc", "europepmc", "clinical_science")):
        return SOURCE_AUTHORITY_WEIGHTS["clinical_science"]
    if "mdn" in low or "mozilla" in low:
        return SOURCE_AUTHORITY_WEIGHTS["mdn"]
    if "arxiv" in low:
        return SOURCE_AUTHORITY_WEIGHTS["arxiv"]
    if "openalex" in low:
        return SOURCE_AUTHORITY_WEIGHTS["openalex"]
    if "wikipedia" in low:
        return SOURCE_AUTHORITY_WEIGHTS["wikipedia"]
    return None


def classify_source_adapter(source_url: str, source_label: str = "") -> str:
    """Maps a lesson URL or source label to one of the canonical adapter keys for the Feed Mixer."""
    combined = f"{source_url or ''} {source_label or ''}".lower()
    if "owasp.org" in combined or "owasp" in combined:
        return "owasp"
    if "ecfr.gov" in combined or "federal regulation" in combined:
        return "ecfr"
    if "osha.gov" in combined or "osha" in combined or "niosh" in combined:
        return "osha"
    if "investopedia.com" in combined or "corporatefinance" in combined or "accounting & financial standard" in combined:
        return "finance"
    if "youtube.com" in combined or "youtu.be" in combined:
        return "youtube"
    if any(k in combined for k in ("geeksforgeeks.org", "tutorialspoint.com", "w3schools.com", "dev.to", "wikibooks technical guide", "engineering guide", "interactive handbook")):
        return "structured_tutorial"
    if any(k in combined for k in ("wikibooks.org", "wikiversity.org", "openstax.org", "opentextbc.ca", "libretexts.org")):
        return "open_textbook"
    if any(k in combined for k in ("ncbi.nlm.nih.gov", "europepmc.org", "ebi.ac.uk")):
        return "clinical_science"
    if "developer.mozilla.org" in combined:
        return "mdn"
    if "arxiv.org" in combined:
        return "arxiv"
    if "openalex.org" in combined or "doi.org" in combined:
        return "openalex"
    if "wikipedia.org" in combined:
        return "wikipedia"
    return "structured_tutorial"


def strip_html_and_clean(html_text: str) -> str:
    """Strips HTML formatting, unescapes entities, and normalizes whitespace."""
    if not html_text:
        return ""
    unescaped = html.unescape(html_text)
    cleaned = re.sub(r"<(script|style|nav|footer|header|aside).*?>.*?</\1>", " ", unescaped, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def distill_skill_query(skill_name: str) -> str:
    """
    Strips bureaucratic O*NET prefix phrasing (e.g., 'Establishing and Maintaining ',
    'Developing and Implementing ', 'Knowledge of ') so search APIs receive clean,
    high-precision technical and domain keywords.
    """
    if not skill_name:
        return ""
    cleaned = re.sub(
        r"^(?:Establishing and Maintaining|Developing and Implementing|Coordinating|Managing|Analyzing|Evaluating|Performing|Operating|Monitoring|Understanding|Knowledge of|Principles of)\s+",
        "",
        skill_name.strip(),
        flags=re.IGNORECASE,
    ).strip()
    return cleaned if len(cleaned) >= 3 else skill_name.strip()


def _extract_article_html(raw_html: str) -> str:
    """Extracts the primary <article> or <main> body from an instructional webpage before stripping tags."""
    if not raw_html:
        return ""
    for tag in ("article", "main"):
        matches = re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", raw_html, flags=re.DOTALL | re.IGNORECASE)
        if matches:
            longest = max(matches, key=len)
            cleaned = strip_html_and_clean(longest)
            if len(cleaned) >= 250:
                return cleaned
    return strip_html_and_clean(raw_html)


def _reconstruct_openalex_abstract(inverted_index: Optional[ Dict[str, List[int]] ]) -> str:
    """Reconstructs readable abstract prose from OpenAlex's abstract_inverted_index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    positions: Dict[int, str] = {}
    for word, pos_list in inverted_index.items():
        if isinstance(pos_list, list):
            for pos in pos_list:
                if isinstance(pos, int):
                    positions[pos] = word
    if not positions:
        return ""
    return " ".join(positions[idx] for idx in sorted(positions.keys()))


def validate_source_content(raw_text: str, skill_name: str) -> bool:
    """
    Gate 1 & 2 Validation:
      1. Minimum substance: Requires at least 200 non-whitespace characters.
      2. Anti-boilerplate & Anti-Anecdote: Rejects disambiguation stubs, empty pages,
         opinion rants, or fabricated generic sentences.
      3. Topical relevance: At least one non-trivial token (or stem) from skill_name
         must appear in the content body.
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
        "enable javascript and cookies to continue",
        "access denied",
    ]
    for stub in stubs:
        if stub in lower_text:
            return False

    stop_words = {"the", "and", "for", "with", "from", "into", "using", "skills", "skill", "general", "basic", "advanced"}
    skill_tokens = [re.sub(r"[^a-zA-Z0-9]", "", t).lower() for t in skill_name.split()]
    meaningful_tokens = [t for t in skill_tokens if len(t) >= 3 and t not in stop_words]
    if meaningful_tokens:
        # Require multiple token matches for multi-token skills to avoid cross-domain collisions
        min_required = 1 if len(meaningful_tokens) <= 2 else 2
        matches_count = sum(
            1 for token in meaningful_tokens
            if (token in lower_text) or (len(token) >= 5 and token[:5] in lower_text)
        )
        if matches_count < min_required:
            return False

    return True


def safe_parse_difficulty(val: Any, default: int = 2) -> int:
    """Safely parses difficulty level 1..5 from int or LLM string like '3 (Intermediate)'."""
    if isinstance(val, (int, float)):
        return max(1, min(5, int(val)))
    if isinstance(val, str):
        m = re.search(r"[1-5]", val)
        if m:
            return int(m.group(0))
    return default


def validate_quiz_structure(quizzes: Any, source_evidence_text: str = "") -> List[Dict[str, Any]]:
    """
    Validates that each quiz item is a well-formed, source-grounded multiple-choice question:
      - 'question': non-empty string (>= 10 chars).
      - 'options': exactly 4 distinct, non-empty options (shuffled server-side with deterministic seed).
      - 'answer': string that exactly matches one of the 4 options.
      - 'explanation': non-empty pedagogical rationale.
      - Grounding check: if source_evidence_text is provided, verifies that key content tokens
        from the answer + explanation + question appear in the source evidence.
    Requires EXACTLY 5 valid items (matching the 5-Question Checkpoint contract).
    """
    if not isinstance(quizzes, list):
        return []

    evidence_lower = (source_evidence_text or "").lower()
    stop_words = {
        "the", "and", "for", "with", "from", "into", "that", "this", "which", "when",
        "what", "where", "while", "should", "would", "could", "because", "correct",
        "option", "answer", "following", "best", "most", "used", "using", "does",
    }

    valid_quizzes = []
    for idx, q in enumerate(quizzes):
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

        # Lexical grounding check against the source evidence
        if len(evidence_lower) >= 200:
            qa_tokens = [
                t for t in re.split(r"[^a-z0-9]+", f"{ans} {explanation} {q_text}".lower())
                if len(t) >= 4 and t not in stop_words
            ]
            if qa_tokens:
                grounded_hits = sum(
                    1 for tok in set(qa_tokens)
                    if tok in evidence_lower or (len(tok) >= 5 and tok[:5] in evidence_lower)
                )
                if grounded_hits < 1:
                    continue

        # Deterministic server-side option shuffle so 'Option A' is never systematically biased
        rng = random.Random(f"{q_text}:{idx}")
        shuffled_opts = list(clean_opts)
        rng.shuffle(shuffled_opts)

        valid_quizzes.append({
            "question": q_text,
            "options": shuffled_opts,
            "answer": ans,
            "explanation": explanation or "Verified against source material.",
        })

    if len(valid_quizzes) < 5:
        return []

    return valid_quizzes[:5]


ADAPTER_DISPLAY_LABELS: Dict[str, str] = {
    "youtube": "YouTube Lecture",
    "structured_tutorial": "Interactive Tutorial",
    "open_textbook": "Open Textbook",
    "clinical_science": "NCBI / Europe PMC",
    "mdn": "MDN Web Docs",
    "arxiv": "arXiv Technical Literature",
    "ecfr": "U.S. Federal Regulation (eCFR)",
    "owasp": "OWASP Security Standard",
    "osha": "OSHA Technical Safety Standard",
    "finance": "Accounting & Financial Standard",
    "openalex": "OpenAlex Academic",
    "wikipedia": "Reference Overview",
}

_YOUTUBE_CACHE_FILE = Path(__file__).resolve().parents[2] / "data" / "youtube_search_cache.json"


def _load_youtube_cache() -> Dict[str, List[tuple]]:
    try:
        if _YOUTUBE_CACHE_FILE.exists():
            data = json.loads(_YOUTUBE_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: [tuple(x) for x in v] for k, v in data.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}


def _save_youtube_cache(cache: Dict[str, List[tuple]]) -> None:
    try:
        _YOUTUBE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _YOUTUBE_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


_YOUTUBE_SEARCH_CACHE: Dict[str, List[tuple]] = _load_youtube_cache()


def hydrate_micro_content_row(
    raw: Dict[str, Any],
    all_skills_map: Optional[Dict[str, Any]] = None,
    fallback_skill_name: str = "Core Skill",
    passed_set: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Unified hydration helper for `micro_content` rows across RecommendationService and DailyDropService.
    Unpacks both top-level columns and `content` JSON metadata so `concept_overview`, `practice_scenario`,
    `video_id`, `source_name`, `source_adapter`, and `quizzes` never disappear on reload.
    """
    c_data: Dict[str, Any] = {}
    c_raw = raw.get("content")
    if isinstance(c_raw, dict):
        c_data = c_raw
    elif isinstance(c_raw, str) and c_raw.strip().startswith("{"):
        try:
            c_data = json.loads(c_raw)
        except Exception:
            c_data = {}

    assoc_skill_id = raw.get("associated_skill_id") or c_data.get("associated_skill_id")
    skill_info = (all_skills_map or {}).get(assoc_skill_id, {})

    quizzes = raw.get("quizzes") or c_data.get("quizzes") or []
    if isinstance(quizzes, str):
        try:
            quizzes = json.loads(quizzes)
        except Exception:
            quizzes = []

    source_url = raw.get("source_url") or c_data.get("source_url") or ""
    source_name = raw.get("source_name") or raw.get("source") or c_data.get("source_name") or ""
    source_adapter = (
        raw.get("source_adapter")
        or c_data.get("source_adapter")
        or classify_source_adapter(source_url, source_name)
    )
    if not source_name:
        source_name = ADAPTER_DISPLAY_LABELS.get(source_adapter, "Instructional Guide")

    summary_bullets = (
        raw.get("summary_bullets")
        or raw.get("summary")
        or c_data.get("summary_bullets")
        or c_data.get("summary")
        or ""
    )
    concept_overview = raw.get("concept_overview") or c_data.get("concept_overview") or ""
    practice_scenario = raw.get("practice_scenario") or c_data.get("practice_scenario") or ""
    video_id = raw.get("video_id") or c_data.get("video_id")
    if not video_id and "youtube.com/watch?v=" in source_url:
        m = re.search(r"v=([A-Za-z0-9_-]{11})", source_url)
        if m:
            video_id = m.group(1)

    difficulty_level = safe_parse_difficulty(raw.get("difficulty_level") or c_data.get("difficulty_level"), default=2)
    trust_score = raw.get("source_trust_score") or c_data.get("source_trust_score") or get_source_trust_score(source_name)

    skill_name = (
        skill_info.get("name")
        or raw.get("skill_name")
        or c_data.get("skill_name")
        or fallback_skill_name
    )
    skill_category = (
        skill_info.get("category")
        or raw.get("skill_category")
        or c_data.get("category")
        or "Technical"
    )

    lid = raw.get("id")
    has_passed = (lid in passed_set) if passed_set is not None else bool(raw.get("has_passed", False))

    return {
        "id": lid,
        "title": raw.get("title", "Lesson"),
        "source_url": source_url,
        "source_name": source_name,
        "source_adapter": source_adapter,
        "video_id": video_id,
        "summary_bullets": summary_bullets,
        "concept_overview": concept_overview,
        "practice_scenario": practice_scenario,
        "difficulty_level": difficulty_level,
        "source_trust_score": trust_score,
        "quizzes": quizzes if isinstance(quizzes, list) else [],
        "associated_skill_id": assoc_skill_id,
        "skill_id": assoc_skill_id,
        "skill_name": skill_name,
        "skill_category": skill_category,
        "career_title": c_data.get("career_title") or raw.get("career_title") or "",
        "has_passed": has_passed,
    }


class ContentService:
    def __init__(self):
        self.ai_service = AIService()
        self.embedding_service = EmbeddingService()
        self._domain_resolution_cache: Dict[str, str] = {}
        self._domain_anchor_vectors: Optional[Dict[str, List[float]]] = None
        self._owasp_catalog: Optional[List[Dict[str, Any]]] = None
        self._pedagogical_anchor_vectors: Optional[Dict[str, List[float]]] = None

    async def verify_pedagogical_substance(
        self,
        candidate_title: str,
        candidate_text: str,
        skill_name: str,
        career_title: str,
    ) -> bool:
        """
        Semantic Vector Gate (Zero Hardcoding, Fail-Closed):
        1. Topical Alignment: Embeds the candidate title + excerpt and verifies cosine similarity
           against the target skill + career query vector (>= 0.56).
        2. Pedagogical vs. Opinion Margin: Compares candidate similarity against an instructional
           curriculum anchor vs. a personal blog/opinion/showcase anchor, rejecting personal
           anecdotes ('Why I like X', 'I built a profile console', 'My career story').
        """
        if not candidate_text or len(candidate_text.strip()) < 220:
            return False

        try:
            if not self._pedagogical_anchor_vectors:
                anchors = {
                    "instructional": (
                        "Comprehensive technical textbook chapter, university lecture notes, reference manual, "
                        "and engineering tutorial explaining core principles, formal definitions, system architecture, "
                        "algorithms, regulatory standards, and step-by-step instructional methodology."
                    ),
                    "opinion_showcase": (
                        "Personal blog post, my personal opinion, why I switched, I built a cool project for my "
                        "GitHub profile, career reflection, vlog, tier list, product comparison rant, or showcase."
                    ),
                }
                keys = list(anchors.keys())
                vecs = await self.embedding_service.get_embeddings_batch(list(anchors.values()))
                self._pedagogical_anchor_vectors = {k: v for k, v in zip(keys, vecs)}

            distilled = distill_skill_query(skill_name)
            target_query = f"{career_title}: {distilled} — technical fundamentals, methodology, and core concepts".strip()
            skill_only_query = f"{distilled} — technical definition, core principles, and methodology".strip()
            cand_snippet = f"{candidate_title}. {candidate_text[:900]}".strip()

            q_vec, sk_vec, c_vec = await self.embedding_service.get_embeddings_batch([target_query, skill_only_query, cand_snippet])
            topical_sim = sum(x * y for x, y in zip(q_vec, c_vec))
            skill_sim = sum(x * y for x, y in zip(sk_vec, c_vec))
            if topical_sim < 0.56 or skill_sim < 0.53:
                logger.debug(
                    f"Vector gate rejected '{candidate_title}' for '{skill_name}' "
                    f"(topical_sim={topical_sim:.3f}, skill_sim={skill_sim:.3f})"
                )
                return False

            inst_vec = self._pedagogical_anchor_vectors["instructional"]
            opin_vec = self._pedagogical_anchor_vectors["opinion_showcase"]
            inst_sim = sum(x * y for x, y in zip(c_vec, inst_vec))
            opin_sim = sum(x * y for x, y in zip(c_vec, opin_vec))

            if opin_sim > inst_sim + 0.015:
                logger.debug(
                    f"Vector gate rejected opinion/showcase '{candidate_title}' "
                    f"(opin_sim={opin_sim:.3f} > inst_sim={inst_sim:.3f})"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"verify_pedagogical_substance failed closed: {e}")
            return False

    async def select_relevant_source_windows(
        self,
        raw_text: str,
        skill_name: str,
        career_title: str,
        max_chars: int = 4200,
    ) -> str:
        """
        Splits long source documents into overlapping ~1,100-char windows, embeds each window,
        and selects the top 4 windows with highest cosine similarity to the target skill + career.
        Prevents long OWASP cheat sheets or textbooks from being truncated to their intro header.
        """
        clean = (raw_text or "").strip()
        if len(clean) <= max_chars:
            return clean

        window_size = 1100
        stride = 900
        windows: List[str] = []
        for start in range(0, min(len(clean), 14000), stride):
            chunk = clean[start : start + window_size].strip()
            if len(chunk) >= 180:
                windows.append(chunk)
            if start + window_size >= len(clean):
                break

        if len(windows) <= 3:
            return clean[:max_chars]

        try:
            distilled = distill_skill_query(skill_name)
            query_str = f"{career_title}: {distilled} — core principles, procedures, rules, and methodology"
            all_vecs = await self.embedding_service.get_embeddings_batch([query_str] + windows)
            q_vec = all_vecs[0]
            w_vecs = all_vecs[1:]

            scored_indices = sorted(
                range(len(windows)),
                key=lambda i: sum(x * y for x, y in zip(q_vec, w_vecs[i])),
                reverse=True,
            )
            # Preserve document reading order among the top 4 most relevant windows
            top_indices = sorted(scored_indices[:4])
            combined = "\n\n---\n\n".join(windows[i] for i in top_indices)
            return combined[:max_chars]
        except Exception as e:
            logger.debug(f"select_relevant_source_windows fallback: {e}")
            return clean[:max_chars]

    # -----------------------------------------------------------------------
    # Modular Source Adapters
    # -----------------------------------------------------------------------

    async def _fetch_youtube_lecture(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
        field_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Adapter 1: YouTube Data API v3 Educational Lectures & Transcripts (Field-Scoped Search Modifiers)."""
        try:
            video_items = []
            field_mod = CAREER_FIELDS.get(field_id, {}).get("youtube_modifier", "tutorial lecture explained")
            clean_career = re.sub(r",.*$", "", career_title or "").strip()
            search_phrase = f"{clean_career} {skill_name} {field_mod}".strip()
            cache_key = f"{field_id}|{skill_name.strip().lower()}"

            if cache_key in _YOUTUBE_SEARCH_CACHE:
                video_items = list(_YOUTUBE_SEARCH_CACHE[cache_key])
            elif settings.youtube_api_key:
                query = quote_plus(search_phrase)
                # Try Category 27 (Education) first, then broad fallback if niche technical query
                for cat_param in ("&videoCategoryId=27", ""):
                    response = await client.get(
                        "https://www.googleapis.com/youtube/v3/search"
                        f"?part=snippet&q={query}&type=video{cat_param}&videoDuration=medium&relevanceLanguage=en&maxResults=6&key={settings.youtube_api_key}",
                        headers={"User-Agent": ACADEMIC_USER_AGENT},
                    )
                    if response.status_code == 200:
                        items = response.json().get("items", [])
                        for entry in items:
                            video_id = entry.get("id", {}).get("videoId")
                            snippet = entry.get("snippet", {})
                            if video_id:
                                video_items.append((
                                    video_id,
                                    html.unescape(snippet.get("title", "")),
                                    snippet.get("description", ""),
                                    snippet.get("channelTitle", ""),
                                ))
                        if video_items:
                            _YOUTUBE_SEARCH_CACHE[cache_key] = list(video_items)
                            _save_youtube_cache(_YOUTUBE_SEARCH_CACHE)
                            break
            else:
                query = quote_plus(search_phrase)
                response = await client.get(
                    f"https://www.youtube.com/results?search_query={query}",
                    headers={"User-Agent": BROWSER_USER_AGENT},
                )
                if response.status_code == 200:
                    ids = list(dict.fromkeys(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)))
                    titles = list(dict.fromkeys(re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}', response.text)))
                    video_items = [(vid, html.unescape(t), "", "") for vid, t in zip(ids[:5], titles[:5])]

            best_candidate = None
            best_char_len = 0

            for video_id, video_title, description, channel_title in video_items[:5]:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                if video_url in excluded or not video_title:
                    continue

                transcript_text = ""
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    transcript = await asyncio.wait_for(
                        asyncio.to_thread(YouTubeTranscriptApi().fetch, video_id, languages=["en"]),
                        timeout=4.0,
                    )
                    transcript_text = " ".join(part.text for part in transcript.snippets)
                except Exception:
                    pass

                # If transcript scraping is blocked/unavailable on this video and we have a YouTube API key,
                # fetch full video snippet from videos.list (search.list truncates descriptions at 160 chars)
                full_desc = description
                if not transcript_text and settings.youtube_api_key:
                    try:
                        v_resp = await client.get(
                            f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={settings.youtube_api_key}",
                            headers={"User-Agent": ACADEMIC_USER_AGENT},
                        )
                        if v_resp.status_code == 200:
                            v_items = v_resp.json().get("items", [])
                            if v_items:
                                v_snip = v_items[0].get("snippet", {})
                                full_desc = v_snip.get("description", "") or description
                                channel_title = v_snip.get("channelTitle", "") or channel_title
                    except Exception:
                        pass

                raw_body = transcript_text if transcript_text else f"Educational Lecture ({channel_title or 'YouTube Education'}): {video_title}. {full_desc}"
                raw = strip_html_and_clean(raw_body)
                if validate_source_content(raw, skill_name):
                    is_pedagogical = await self.verify_pedagogical_substance(
                        candidate_title=video_title,
                        candidate_text=raw,
                        skill_name=skill_name,
                        career_title=career_title,
                    )
                    if not is_pedagogical:
                        continue
                    source_label = f"YouTube Lecture ({channel_title})" if channel_title else ("YouTube transcript" if transcript_text else "YouTube lecture")
                    candidate = {
                        "title": html.unescape(video_title).strip()[:140],
                        "source_url": video_url,
                        "raw_text": raw[:10000],
                        "source": source_label,
                        "source_adapter": "youtube",
                        "video_id": video_id,
                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["youtube"],
                    }
                    # If we got a full transcript or a comprehensive syllabus description (>= 500 chars), return immediately
                    if transcript_text or len(raw) >= 500:
                        return candidate
                    if len(raw) > best_char_len:
                        best_char_len = len(raw)
                        best_candidate = candidate

            if best_candidate:
                return best_candidate
        except Exception as e:
            logger.debug(f"YouTube adapter error: {e}")
        return None

    async def _fetch_structured_tutorial(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        category: str,
        excluded: set,
        career_title: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Adapter 2: Open Technical Handbooks & University Courseware Search API
        (Wikibooks & Wikiversity Full-Text Search APIs + Semantic Pedagogical Verification).
        Zero hardcoded slug maps, zero personal blog/opinion feeds.
        """
        distilled = distill_skill_query(skill_name)
        clean_career = re.sub(r",.*$", "", career_title or "").strip()
        apis = [
            ("https://en.wikibooks.org/w/api.php", "https://en.wikibooks.org/wiki/", "Wikibooks Technical Guide"),
            ("https://en.wikiversity.org/w/api.php", "https://en.wikiversity.org/wiki/", "Wikiversity Courseware"),
        ]
        search_queries = [
            f"{distilled} {clean_career}".strip(),
            f"{distilled} tutorial".strip(),
            distilled,
        ]
        for api_url, wiki_base, provider_label in apis:
            for q in search_queries:
                if not q:
                    continue
                try:
                    wb_resp = await client.get(
                        f"{api_url}?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=4",
                        headers={"User-Agent": ACADEMIC_USER_AGENT},
                    )
                    if wb_resp.status_code != 200:
                        continue
                    for item in wb_resp.json().get("query", {}).get("search", []):
                        page_title = item.get("title", "")
                        if not page_title or ":" in page_title:
                            continue
                        page_url = f"{wiki_base}{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"{api_url}?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers={"User-Agent": ACADEMIC_USER_AGENT},
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if len(extract) >= 350 and validate_source_content(extract, distilled):
                                    is_pedagogical = await self.verify_pedagogical_substance(
                                        candidate_title=page_title,
                                        candidate_text=extract,
                                        skill_name=distilled,
                                        career_title=career_title or category,
                                    )
                                    if is_pedagogical:
                                        return {
                                            "title": f"{page_title} ({provider_label})"[:140],
                                            "source_url": page_url,
                                            "raw_text": extract[:10000],
                                            "source": provider_label,
                                            "source_adapter": "structured_tutorial",
                                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["structured_tutorial"],
                                        }
                except Exception as e:
                    logger.debug(f"{provider_label} structured tutorial search error: {e}")
        return None

    async def _fetch_mdn_docs(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        category: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 3: MDN Web Docs Official Search API (Web standards, JavaScript, CSS, HTML, Web APIs)."""
        distilled = distill_skill_query(skill_name)
        distilled_lower = distilled.lower()

        # MDN is strictly for Web Standards (HTML, CSS, JS, HTTP, Web APIs).
        # Reject non-web competencies (relational databases, statistical modeling, data warehousing, kernel)
        non_mdn_keywords = (
            "sql", "database", "relational", "r statistical", "time series", "arima",
            "docker", "kubernetes", "linux", "snowflake", "warehouse", "kernel",
            "pandas", "numpy", "pytorch", "tensorflow", "tableau", "power bi", "nosql", "mongodb"
        )
        if any(k in distilled_lower for k in non_mdn_keywords):
            return None
        try:
            q = quote_plus(distilled)
            resp = await client.get(
                f"https://developer.mozilla.org/api/v1/search?q={q}&locale=en-US",
                headers={"User-Agent": ACADEMIC_USER_AGENT},
            )
            if resp.status_code == 200:
                docs = resp.json().get("documents", [])
                for doc in docs[:5]:
                    raw_url = doc.get("mdn_url", "")
                    if not raw_url:
                        continue
                    # Reject glossary definitions, stubs, and meta pages (e.g. /docs/Glossary/*)
                    if "/glossary/" in raw_url.lower():
                        continue
                    mdn_url = f"https://developer.mozilla.org{raw_url}"
                    if mdn_url in excluded:
                        continue
                    summary = doc.get("summary", "")
                    title = doc.get("title", distilled)
                    page_resp = await client.get(mdn_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
                    body_text = _extract_article_html(page_resp.text) if page_resp.status_code == 200 else summary
                    if len(body_text.strip()) < 500:
                        continue
                    combined = f"{title}. {summary}\n\n{body_text}".strip()
                    if validate_source_content(combined, distilled):
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=title,
                            candidate_text=combined,
                            skill_name=distilled,
                            career_title=career_title or category,
                        )
                        if is_pedagogical:
                            return {
                                "title": f"{title} (MDN Web Docs)",
                                "source_url": mdn_url,
                                "raw_text": combined[:10000],
                                "source": "MDN Web Docs",
                                "source_adapter": "mdn",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["mdn"],
                            }
        except Exception as e:
            logger.debug(f"MDN adapter error: {e}")
        return None

    async def _fetch_open_textbook(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 4: Wikibooks & Wikiversity Open Courseware / Textbooks (All Careers & Trades)."""
        distilled = distill_skill_query(skill_name)
        apis = [
            ("https://en.wikibooks.org/w/api.php", "https://en.wikibooks.org/wiki/", "Wikibooks"),
            ("https://en.wikiversity.org/w/api.php", "https://en.wikiversity.org/wiki/", "Wikiversity"),
        ]
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for api_url, wiki_base, label in apis:
            clean_career = re.sub(r",.*$", "", career_title or "").strip()
            for query_str in (f"{distilled} {clean_career}".strip(), distilled):
                try:
                    srch = await client.get(
                        f"{api_url}?action=query&list=search&srsearch={quote_plus(query_str)}&utf8=&format=json&srlimit=3",
                        headers=headers,
                    )
                    if srch.status_code != 200:
                        continue
                    results = srch.json().get("query", {}).get("search", [])
                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or ":" in page_title:
                            continue
                        page_url = f"{wiki_base}{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"{api_url}?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers=headers,
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                tokens = [t.lower() for t in distilled.split() if len(t) >= 4]
                                best_idx = -1
                                for tok in tokens:
                                    idx = extract.lower().find(tok)
                                    if idx != -1:
                                        best_idx = idx
                                        break
                                start_idx = max(0, best_idx - 200) if best_idx != -1 else 0
                                slice_text = extract[start_idx:start_idx + 8000]
                                if validate_source_content(slice_text, distilled):
                                    is_pedagogical = await self.verify_pedagogical_substance(
                                        candidate_title=page_title,
                                        candidate_text=slice_text,
                                        skill_name=distilled,
                                        career_title=career_title,
                                    )
                                    if not is_pedagogical:
                                        continue
                                    tb_domain = await self.resolve_career_domain(page_title, slice_text[:300])
                                    tgt_domain = await self.resolve_career_domain(career_title, distilled)
                                    if tgt_domain not in {"general", ""} and tb_domain not in {"general", ""} and tb_domain != tgt_domain:
                                        logger.info(f"Semantically rejecting open textbook '{page_title}' ({tb_domain}) for career '{career_title}' ({tgt_domain})")
                                        continue
                                    return {
                                        "title": page_title,
                                        "source_url": page_url,
                                        "raw_text": slice_text,
                                        "source": label,
                                        "source_adapter": "open_textbook",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["open_textbook"],
                                    }
                except Exception as e:
                    logger.debug(f"{label} adapter error: {e}")
        return None

    async def _fetch_clinical_and_science(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 5: Europe PMC & NCBI Bookshelf / StatPearls (Healthcare, Bioscience, Engineering, Safety)."""
        distilled = distill_skill_query(skill_name)
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        clean_career = re.sub(r",.*$", "", career_title or "").strip()
        queries = [
            f'"{distilled}" AND ({clean_career})' if clean_career else f'"{distilled}"',
            f"{distilled} {clean_career}".strip() if clean_career else distilled,
            distilled,
        ]
        for query_str in queries:
            try:
                resp = await client.get(
                    f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(query_str)}&resultType=core&format=json&pageSize=5",
                    headers=headers,
                )
                if resp.status_code == 200:
                    results = resp.json().get("resultList", {}).get("result", [])
                    for art in results:
                        abstract = strip_html_and_clean(art.get("abstractText", ""))
                        title = strip_html_and_clean(art.get("title", "")).rstrip(".")
                        pmid = art.get("pmid") or art.get("id")
                        pmcid = art.get("pmcid")
                        if pmcid:
                            art_url = f"https://europepmc.org/article/MED/{pmid}" if pmid else f"https://europepmc.org/articles/{pmcid}"
                        elif pmid:
                            art_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                        else:
                            continue
                        if art_url in excluded:
                            continue
                        combined = f"{title}.\n\n{abstract}".strip()
                        if validate_source_content(combined, distilled):
                            is_pedagogical = await self.verify_pedagogical_substance(
                                candidate_title=title,
                                candidate_text=combined,
                                skill_name=distilled,
                                career_title=career_title,
                            )
                            if is_pedagogical:
                                return {
                                    "title": title[:140],
                                    "source_url": art_url,
                                    "raw_text": combined[:8000],
                                    "source": "Europe PMC / NCBI",
                                    "source_adapter": "clinical_science",
                                    "trust_score": SOURCE_AUTHORITY_WEIGHTS["clinical_science"],
                                }
            except Exception as e:
                logger.debug(f"EuropePMC/NCBI adapter error: {e}")
        return None

    async def _fetch_openalex_chapter(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 6: OpenAlex Peer-Reviewed Book Chapters & Review Articles (Finance, Law, Management, Engineering)."""
        distilled = distill_skill_query(skill_name)
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for search_q in (f"{distilled} {career_title}".strip(), distilled):
            try:
                resp = await client.get(
                    f"https://api.openalex.org/works?search={quote_plus(search_q)}&per-page=5&sort=cited_by_count:desc",
                    headers=headers,
                )
                if resp.status_code == 200:
                    works = resp.json().get("results", [])
                    for w in works:
                        if w.get("cited_by_count", 0) < 2:
                            continue
                        title = strip_html_and_clean(w.get("title") or w.get("display_name") or "")
                        abstract = _reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
                        landing_url = (
                            (w.get("primary_location") or {}).get("landing_page_url")
                            or w.get("doi")
                            or w.get("id")
                        )
                        if not landing_url or landing_url in excluded:
                            continue
                        combined = f"{title}.\n\n{abstract}".strip()
                        if validate_source_content(combined, distilled):
                            is_pedagogical = await self.verify_pedagogical_substance(
                                candidate_title=title,
                                candidate_text=combined,
                                skill_name=distilled,
                                career_title=career_title,
                            )
                            if is_pedagogical:
                                return {
                                    "title": title[:140],
                                    "source_url": landing_url,
                                    "raw_text": combined[:8000],
                                    "source": "OpenAlex Academic",
                                    "source_adapter": "openalex",
                                    "trust_score": SOURCE_AUTHORITY_WEIGHTS["openalex"],
                                }
            except Exception as e:
                logger.debug(f"OpenAlex adapter error: {e}")
        return None

    async def _fetch_wikipedia_fallback(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        excluded: set,
        career_title: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Adapter 7: Wikipedia Multi-Section Extracts (Strictly Last-Resort Fallback + Semantic Gate)."""
        distilled = distill_skill_query(skill_name)
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        slug = distilled.replace(" ", "_")
        try:
            r_wiki = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug)}", headers=headers)
            if r_wiki.status_code == 200:
                d = r_wiki.json()
                extract = d.get("extract", "")
                cand_title = d.get("title", distilled)
                if d.get("type") == "standard" and validate_source_content(extract, distilled):
                    page_url = d.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug}"
                    if page_url not in excluded:
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=cand_title,
                            candidate_text=extract,
                            skill_name=distilled,
                            career_title=career_title,
                        )
                        if is_pedagogical:
                            return {
                                "title": cand_title,
                                "source_url": page_url,
                                "raw_text": extract[:5000],
                                "source": "wikipedia",
                                "source_adapter": "wikipedia",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                            }
        except Exception as e:
            logger.debug(f"Wikipedia summary error: {e}")

        search_queries = [f"{distilled} {career_title}".strip(), distilled]
        for q in search_queries:
            try:
                r_srch = await client.get(
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=5",
                    headers=headers,
                )
                if r_srch.status_code == 200:
                    results = r_srch.json().get("query", {}).get("search", [])
                    for res_item in results[:5]:
                        cand_title = res_item.get("title", "")
                        if not cand_title or ":" in cand_title or "disambiguation" in cand_title.lower():
                            continue
                        slug2 = cand_title.replace(" ", "_")
                        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(slug2)}"
                        if page_url in excluded:
                            continue
                        r_sum = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug2)}", headers=headers)
                        if r_sum.status_code == 200:
                            d2 = r_sum.json()
                            extract2 = d2.get("extract", "")
                            if d2.get("type") == "standard" and validate_source_content(extract2, distilled):
                                is_pedagogical = await self.verify_pedagogical_substance(
                                    candidate_title=cand_title,
                                    candidate_text=extract2,
                                    skill_name=distilled,
                                    career_title=career_title,
                                )
                                if is_pedagogical:
                                    return {
                                        "title": d2.get("title", cand_title),
                                        "source_url": page_url,
                                        "raw_text": extract2[:5000],
                                        "source": "wikipedia",
                                        "source_adapter": "wikipedia",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                                    }
            except Exception as e:
                logger.debug(f"Wikipedia search fallback error for '{q}': {e}")
        return None


    async def _fetch_owasp_cheatsheet(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """
        Adapter: OWASP Official Security Standards (Dynamic GitHub Tree Index + Vector Cosine Matching).
        Zero hardcoded keyword-to-filename tuples.
        """
        distilled = distill_skill_query(skill_name)
        try:
            if not self._owasp_catalog:
                idx_url = "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/Index.md"
                idx_resp = await client.get(idx_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
                entries: List[Dict[str, Any]] = []
                if idx_resp.status_code == 200 and idx_resp.text:
                    matches = re.findall(r"\[([^\]]+)\]\(cheatsheets/([A-Za-z0-9_-]+\.md)\)", idx_resp.text)
                    seen_files = set()
                    for label, fname in matches:
                        if fname not in seen_files:
                            seen_files.add(fname)
                            entries.append({"label": label.strip(), "filename": fname.strip()})
                if not entries:
                    # Fallback: derive readable titles from OWASP GitHub directory listing API
                    api_resp = await client.get(
                        "https://api.github.com/repos/OWASP/CheatSheetSeries/contents/cheatsheets",
                        headers={"User-Agent": ACADEMIC_USER_AGENT},
                    )
                    if api_resp.status_code == 200 and isinstance(api_resp.json(), list):
                        for item in api_resp.json():
                            fname = str(item.get("name") or "")
                            if fname.endswith("_Cheat_Sheet.md"):
                                label = fname.replace("_Cheat_Sheet.md", "").replace("_", " ")
                                entries.append({"label": label, "filename": fname})
                if entries:
                    texts = [f"OWASP Security Standard: {e['label']}" for e in entries]
                    vecs = await self.embedding_service.get_embeddings_batch(texts)
                    for e, v in zip(entries, vecs):
                        e["vector"] = v
                    self._owasp_catalog = entries

            if not self._owasp_catalog:
                return None

            q_vec = await self.embedding_service.get_embedding(f"{career_title}: {distilled} security standard")
            scored = sorted(
                self._owasp_catalog,
                key=lambda item: sum(x * y for x, y in zip(q_vec, item["vector"])),
                reverse=True,
            )

            for candidate in scored[:3]:
                sim = sum(x * y for x, y in zip(q_vec, candidate["vector"]))
                if sim < 0.58:
                    break
                selected_file = candidate["filename"]
                display_label = candidate["label"]
                raw_url = f"https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/{selected_file}"
                public_url = f"https://cheatsheetseries.owasp.org/cheatsheets/{selected_file.replace('.md', '.html')}"
                if public_url in excluded or raw_url in excluded:
                    continue

                resp = await client.get(raw_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
                if resp.status_code == 200 and resp.text:
                    raw_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", resp.text)
                    raw_text = re.sub(r"```[\s\S]*?```", " ", raw_text)
                    raw_text = re.sub(r"#+\s*", "", raw_text)
                    cleaned = strip_html_and_clean(raw_text)
                    if len(cleaned) >= 300:
                        return {
                            "title": f"OWASP {display_label}: {distilled}"[:140],
                            "source_url": public_url,
                            "raw_text": cleaned[:10000],
                            "source": "OWASP Security Standard",
                            "source_adapter": "owasp",
                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["owasp"],
                        }
        except Exception as e:
            logger.debug(f"OWASP adapter error: {e}")
        return None

    async def _fetch_osha_standards(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter: OSHA 29 CFR Federal Safety Standards & Wikibooks Engineering/Trades Manuals."""
        distilled = distill_skill_query(skill_name)
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        # 1. Query U.S. eCFR Title 29 (OSHA Labor & Occupational Safety Regulations)
        try:
            q_str = quote_plus(f"OSHA {distilled}".strip())
            api_url = f"https://www.ecfr.gov/api/search/v1/results?query={q_str}&per_page=4&page=1"
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                snippets = []
                primary_url = ""
                primary_heading = ""
                for r in results:
                    headings = r.get("headings") or {}
                    hierarchy = r.get("hierarchy") or {}
                    title_num = hierarchy.get("title") or "29"
                    part_num = hierarchy.get("part") or ""
                    sec_num = hierarchy.get("section") or ""
                    part_label = headings.get("section") or headings.get("part") or distilled
                    excerpt = strip_html_and_clean(r.get("full_text_excerpt") or "")
                    if excerpt and len(excerpt) >= 60:
                        snippets.append(f"[{part_label}] {excerpt}")
                        if not primary_url:
                            primary_heading = strip_html_and_clean(str(part_label))
                            if sec_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/section-{sec_num}"
                            elif part_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/part-{part_num}"
                            else:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}"
                if snippets and primary_url and primary_url not in excluded:
                    combined = f"OSHA Technical Safety Standard ({career_title} — {distilled}): " + " ".join(snippets)
                    if validate_source_content(combined, distilled):
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=primary_heading or distilled,
                            candidate_text=combined,
                            skill_name=distilled,
                            career_title=career_title,
                        )
                        if is_pedagogical:
                            return {
                                "title": f"OSHA Standard: {primary_heading or distilled}"[:140],
                                "source_url": primary_url,
                                "raw_text": combined[:10000],
                                "source": "OSHA / Technical Safety Standard",
                                "source_adapter": "osha",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["osha"],
                            }
        except Exception as e:
            logger.debug(f"OSHA eCFR query error: {e}")

        # 2. Fallback to Wikibooks Engineering / Trade Manuals
        trade_queries = [
            f"Occupational safety {distilled}".strip(),
            f"Engineering {distilled}".strip(),
        ]
        for q in trade_queries:
            try:
                srch = await client.get(
                    f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=3",
                    headers=headers,
                )
                if srch.status_code == 200:
                    results = srch.json().get("query", {}).get("search", [])
                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or ":" in page_title:
                            continue
                        page_url = f"https://en.wikibooks.org/wiki/{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"https://en.wikibooks.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers=headers,
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if validate_source_content(extract, distilled):
                                    is_pedagogical = await self.verify_pedagogical_substance(
                                        candidate_title=page_title,
                                        candidate_text=extract,
                                        skill_name=distilled,
                                        career_title=career_title,
                                    )
                                    if is_pedagogical:
                                        return {
                                            "title": f"Technical Safety Manual: {page_title}"[:140],
                                            "source_url": page_url,
                                            "raw_text": extract[:10000],
                                            "source": "OSHA / Technical Safety Standard",
                                            "source_adapter": "osha",
                                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["osha"],
                                        }
            except Exception as e:
                logger.debug(f"OSHA Wikibooks adapter error: {e}")
        return None

    async def _fetch_finance_knowledge(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter: Financial Reporting, SEC & Banking Standards (U.S. eCFR Titles 12/17 + Wikibooks Corporate Finance)."""
        distilled = distill_skill_query(skill_name)
        headers = {"User-Agent": ACADEMIC_USER_AGENT}

        # 1. Primary API: Wikibooks Corporate Finance & Accounting Textbooks (High Pedagogical Alignment)
        finance_queries = [
            f"Financial Accounting {distilled}".strip(),
            f"Corporate Finance {distilled}".strip(),
            distilled,
        ]
        for q in finance_queries:
            try:
                srch = await client.get(
                    f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=3",
                    headers=headers,
                )
                if srch.status_code == 200:
                    results = srch.json().get("query", {}).get("search", [])
                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or ":" in page_title:
                            continue
                        page_url = f"https://en.wikibooks.org/wiki/{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"https://en.wikibooks.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers=headers,
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if validate_source_content(extract, distilled):
                                    is_pedagogical = await self.verify_pedagogical_substance(
                                        candidate_title=page_title,
                                        candidate_text=extract,
                                        skill_name=distilled,
                                        career_title=career_title,
                                    )
                                    if is_pedagogical:
                                        return {
                                            "title": f"Accounting & Financial Standard: {page_title}"[:140],
                                            "source_url": page_url,
                                            "raw_text": extract[:10000],
                                            "source": "Accounting & Financial Standard",
                                            "source_adapter": "finance",
                                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["finance"],
                                        }
            except Exception as e:
                logger.debug(f"Finance knowledge adapter error: {e}")

        # 2. Secondary API: U.S. Federal eCFR Financial & Securities Regulations (Title 17 SEC / Title 12 Banking)
        try:
            q_str = quote_plus(f"financial {distilled}".strip())
            api_url = f"https://www.ecfr.gov/api/search/v1/results?query={q_str}&per_page=4&page=1"
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                snippets = []
                primary_url = ""
                primary_heading = ""
                for r in results:
                    headings = r.get("headings") or {}
                    hierarchy = r.get("hierarchy") or {}
                    title_num = hierarchy.get("title") or "17"
                    part_num = hierarchy.get("part") or ""
                    sec_num = hierarchy.get("section") or ""
                    part_label = headings.get("section") or headings.get("part") or distilled
                    excerpt = strip_html_and_clean(r.get("full_text_excerpt") or "")
                    if excerpt and len(excerpt) >= 60:
                        snippets.append(f"[{part_label}] {excerpt}")
                        if not primary_url:
                            primary_heading = strip_html_and_clean(str(part_label))
                            if sec_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/section-{sec_num}"
                            elif part_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/part-{part_num}"
                            else:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}"
                if snippets and primary_url and primary_url not in excluded:
                    combined = f"Financial & Accounting Regulatory Standard ({career_title} — {distilled}): " + " ".join(snippets)
                    if validate_source_content(combined, distilled):
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=primary_heading or distilled,
                            candidate_text=combined,
                            skill_name=distilled,
                            career_title=career_title,
                        )
                        if is_pedagogical:
                            return {
                                "title": f"Financial Standard: {primary_heading or distilled}"[:140],
                                "source_url": primary_url,
                                "raw_text": combined[:10000],
                                "source": "Accounting & Financial Standard",
                                "source_adapter": "finance",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["finance"],
                            }
        except Exception as e:
            logger.debug(f"Finance eCFR query error: {e}")
        return None

    async def _fetch_arxiv_technical(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """
        Adapter 6B: arXiv Open-Access Technical & Quantitative Literature (export.arxiv.org Atom API).
        Serves Software/AI (`cs`, `stat`), Science (`q-bio`, `physics`), Engineering (`eess`), and Quantitative Finance (`q-fin`).
        """
        distilled = distill_skill_query(skill_name)
        try:
            query = quote_plus(f'all:"{distilled}" AND all:{career_title.split()[0] if career_title else distilled}')
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=4"
            resp = await client.get(url, headers={"User-Agent": ACADEMIC_USER_AGENT})
            if resp.status_code == 200 and "<entry>" in resp.text:
                entries = re.findall(r"<entry>(.*?)</entry>", resp.text, flags=re.DOTALL)
                for entry in entries:
                    id_m = re.search(r"<id>(.*?)</id>", entry)
                    title_m = re.search(r"<title>(.*?)</title>", entry, flags=re.DOTALL)
                    sum_m = re.search(r"<summary>(.*?)</summary>", entry, flags=re.DOTALL)
                    if not id_m or not title_m or not sum_m:
                        continue
                    paper_url = id_m.group(1).strip()
                    if paper_url in excluded:
                        continue
                    paper_title = re.sub(r"\s+", " ", title_m.group(1)).strip()
                    summary_text = strip_html_and_clean(sum_m.group(1))
                    full_text = f"Technical Literature: {paper_title}. {summary_text}"
                    if validate_source_content(full_text, distilled):
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=paper_title,
                            candidate_text=full_text,
                            skill_name=distilled,
                            career_title=career_title,
                        )
                        if is_pedagogical:
                            return {
                                "title": f"{distilled}: {paper_title}"[:140],
                                "source_url": paper_url,
                                "raw_text": full_text[:10000],
                                "source": "arXiv Technical Literature",
                                "source_adapter": "arxiv",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["arxiv"],
                            }
        except Exception as e:
            logger.debug(f"arXiv adapter error: {e}")
        return None

    async def _fetch_ecfr_regulations(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """
        Adapter 6C: U.S. Code of Federal Regulations REST API (ecfr.gov/api/search/v1/results).
        Provides verbatim regulatory standards for FAA Aviation (14 CFR), OSHA Safety (29 CFR),
        FDA/HACCP Food & Drug Compliance (21 CFR), EPA Refrigerants/Environment (40 CFR), and SEC Finance (17 CFR).
        """
        distilled = distill_skill_query(skill_name)
        try:
            q_str = quote_plus(f"{distilled} {career_title}".strip())
            api_url = f"https://www.ecfr.gov/api/search/v1/results?query={q_str}&per_page=4&page=1"
            resp = await client.get(api_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                snippets = []
                primary_url = ""
                primary_heading = ""
                for r in results:
                    headings = r.get("headings") or {}
                    hierarchy = r.get("hierarchy") or {}
                    title_num = hierarchy.get("title") or r.get("structure_index") or headings.get("title") or ""
                    part_num = hierarchy.get("part") or ""
                    sec_num = hierarchy.get("section") or ""
                    part_label = headings.get("section") or headings.get("part") or distilled
                    excerpt = strip_html_and_clean(r.get("full_text_excerpt") or "")
                    if excerpt and len(excerpt) >= 60:
                        snippets.append(f"[{part_label}] {excerpt}")
                        if not primary_url:
                            primary_heading = strip_html_and_clean(str(part_label))
                            if str(title_num).isdigit() and sec_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/section-{sec_num}"
                            elif str(title_num).isdigit() and part_num:
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}/part-{part_num}"
                            elif str(title_num).isdigit():
                                primary_url = f"https://www.ecfr.gov/current/title-{title_num}"
                            else:
                                primary_url = f"https://www.ecfr.gov/current/title-29"
                if snippets and primary_url and primary_url not in excluded:
                    combined_text = f"Federal Regulatory Standard ({career_title} — {distilled}): " + " ".join(snippets)
                    if validate_source_content(combined_text, distilled):
                        is_pedagogical = await self.verify_pedagogical_substance(
                            candidate_title=primary_heading or distilled,
                            candidate_text=combined_text,
                            skill_name=distilled,
                            career_title=career_title,
                        )
                        if is_pedagogical:
                            return {
                                "title": f"Federal Standard: {primary_heading or distilled}"[:140],
                                "source_url": primary_url,
                                "raw_text": combined_text[:10000],
                                "source": "U.S. Code of Federal Regulations (eCFR)",
                                "source_adapter": "ecfr",
                                "trust_score": SOURCE_AUTHORITY_WEIGHTS["ecfr"],
                            }
        except Exception as e:
            logger.debug(f"eCFR regulatory adapter error: {e}")
        return None

    async def resolve_career_domain(
        self,
        career_title: str,
        skill_name: str,
        category: str = "",
        onet_soc_code: Optional[str] = None,
    ) -> str:
        """
        Determines the occupational domain (health | tech | finance | safety_trades | security | general)
        using a two-tier hierarchy:
          1. Deterministic O*NET SOC Major Group (for catalog-backed occupations).
          2. Semantic Embedding Vector Centroids (for novel AI-suggested or frontier occupations).
        Zero hardcoded substring matching.
        """
        if onet_soc_code:
            prefix = str(onet_soc_code).strip()[:2]
            if prefix in {"29", "31"}:
                return "health"
            if prefix == "15":
                return "tech"
            if prefix == "17":
                return "engineering"
            if prefix == "19":
                return "science"
            if prefix in {"11", "43"}:
                return "business_admin"
            if prefix in {"13", "41"}:
                return "finance"
            if prefix in {"33", "47", "49", "51"}:
                return "safety_trades"
            if prefix == "53":
                return "transportation"

        # Tier 2: Semantic Vector Cosine Similarity against Domain Anchors
        cache_key = f"{career_title}|{category}|{skill_name}".lower().strip()
        if cache_key in self._domain_resolution_cache:
            return self._domain_resolution_cache[cache_key]

        if not self._domain_anchor_vectors:
            # Authoritative BLS SOC cluster occupational definitions:
            # Replaces arbitrary keyword dumps with verified standard occupational group profiles
            anchors = {
                "tech": "Computer and Information Technology: Software engineering, cloud infrastructure, microservices architecture, system design, databases, web development, algorithms, programming.",
                "engineering": "Architecture and Engineering: Aerospace engineering, mechanical systems, civil engineering, electrical circuits, structural blueprints, robotics hardware.",
                "health": "Healthcare and Medical: Clinical diagnosis, patient care, nursing, dentistry, oral surgery, pharmacy, medical therapy, surgical treatment.",
                "science": "Life, Physical and Social Sciences: Scientific research, biochemistry, laboratory methodology, physics, molecular biology, chemistry.",
                "security": "Cybersecurity and InfoSec: Network security, threat detection, penetration testing, cryptographic protocols, incident response, security auditing.",
                "finance": "Financial Specialists: Accounting, financial analysis, investment valuation, quantitative modeling, auditing, portfolio management.",
                "business_admin": "Business Operations and Administration: Office management, clerical operations, executive administration, organizational coordination, human resources.",
                "safety_trades": "Trades and Construction: Electrical wiring, industrial mechanics, plumbing, HVAC maintenance, occupational safety, carpentry.",
                "transportation": "Aviation and Transportation: Flight crew, airline piloting, commercial flight navigation, air traffic control, cargo logistics.",
            }
            anchor_keys = list(anchors.keys())
            anchor_texts = list(anchors.values())
            vectors = await self.embedding_service.get_embeddings_batch(anchor_texts)
            self._domain_anchor_vectors = {k: v for k, v in zip(anchor_keys, vectors)}

        query_text = f"{career_title} {category} {skill_name}".strip()
        query_vector = await self.embedding_service.get_embedding(query_text)

        scores = {
            d: sum(x * y for x, y in zip(query_vector, v))
            for d, v in self._domain_anchor_vectors.items()
        }
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_domain, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_score - second_score
        resolved = best_domain if (best_score >= 0.60 and margin >= 0.005) else "general"
        self._domain_resolution_cache[cache_key] = resolved
        return resolved

    async def fetch_live_source_for_skill(
        self,
        skill_name: str,
        category: str = "Core",
        career_title: str = "",
        exclude_source_urls: Optional[set] = None,
        preferred_adapters: Optional[List[str]] = None,
        onet_soc_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes the modular instructional source pipeline for any career and skill.
        Prioritizes active teaching sources (YouTube lectures, GeeksforGeeks/Tutorialspoint/W3Schools,
        MDN Web Docs, Wikibooks/Wikiversity Open Textbooks, NCBI/EuropePMC, arXiv, eCFR, OpenAlex) and uses
        Wikipedia strictly as a last-resort fallback.
        """
        excluded = {u for u in (exclude_source_urls or set()) if u}
        domain = await self.resolve_career_domain(
            career_title, skill_name, category=category, onet_soc_code=onet_soc_code
        )
        field_meta = classify_career_field(career_title, onet_soc_code)
        field_id = field_meta["field_id"]

        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            # Build 7-Field domain-aware adapter execution order (100% aligned with RESTRICTED_ADAPTER_DOMAINS)
            adapter_order = []
            if field_id == "trades_safety" or domain in ("safety_trades", "transportation"):
                adapter_order.extend([
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("ecfr", lambda: self._fetch_ecfr_regulations(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="trades_safety")),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif field_id == "healthcare" or domain == "health":
                adapter_order.extend([
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="healthcare")),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("ecfr", lambda: self._fetch_ecfr_regulations(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif field_id == "engineering" or domain == "engineering":
                adapter_order.extend([
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="engineering")),
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("ecfr", lambda: self._fetch_ecfr_regulations(client, skill_name, career_title, excluded)),
                    ("arxiv", lambda: self._fetch_arxiv_technical(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif field_id == "finance" or domain == "finance":
                adapter_order.extend([
                    ("finance", lambda: self._fetch_finance_knowledge(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="finance")),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("ecfr", lambda: self._fetch_ecfr_regulations(client, skill_name, career_title, excluded)),
                    ("arxiv", lambda: self._fetch_arxiv_technical(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif field_id == "science" or domain == "science":
                adapter_order.extend([
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="science")),
                    ("arxiv", lambda: self._fetch_arxiv_technical(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                ])
            elif field_id == "tech" or domain in ("tech", "security"):
                if domain == "security":
                    adapter_order.extend([
                        ("owasp", lambda: self._fetch_owasp_cheatsheet(client, skill_name, career_title, excluded)),
                        ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="tech")),
                        ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                        ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded, career_title=career_title)),
                        ("arxiv", lambda: self._fetch_arxiv_technical(client, skill_name, career_title, excluded)),
                        ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ])
                else:
                    adapter_order.extend([
                        ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="tech")),
                        ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                        ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded, career_title=career_title)),
                        ("owasp", lambda: self._fetch_owasp_cheatsheet(client, skill_name, career_title, excluded)),
                        ("arxiv", lambda: self._fetch_arxiv_technical(client, skill_name, career_title, excluded)),
                        ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                        ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ])
            else:
                # Field 6 (`business_ops`): Operations, Management, Legal & Digital Media
                adapter_order.extend([
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded, field_id="business_ops")),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded, career_title=career_title)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])

            # If caller requested specific preferred adapters (e.g., Mixer diversity), move them to front
            if preferred_adapters:
                pref_set = set(preferred_adapters)
                adapter_order.sort(key=lambda pair: 0 if pair[0] in pref_set else 1)

            # Execute adapters in concurrent 2-adapter waves for fast, non-blocking source discovery
            for wave_idx in range(0, len(adapter_order), 2):
                wave = adapter_order[wave_idx : wave_idx + 2]
                results = await asyncio.gather(
                    *(fn() for _, fn in wave),
                    return_exceptions=True,
                )
                for res in results:
                    if isinstance(res, dict) and res.get("source_url"):
                        # If YouTube lecture has short description (< 800 chars, e.g. transcripts blocked),
                        # augment with a written companion textbook / tutorial / documentation source
                        # so downstream lesson atomization and 5-quiz checkpoints have deep pedagogical grounding.
                        if res.get("source_adapter") == "youtube" and len(res.get("raw_text", "")) < 800:
                            for name, fn in adapter_order:
                                if name != "youtube":
                                    try:
                                        comp = await fn()
                                        if isinstance(comp, dict) and comp.get("raw_text"):
                                            res["raw_text"] = (
                                                f"{res['raw_text']}\n\n"
                                                f"Companion Text Reference ({comp.get('source', 'Curated Source')}):\n"
                                                f"{comp['raw_text']}"
                                            )
                                            res["companion_source"] = comp.get("source")
                                            res["companion_url"] = comp.get("source_url")
                                            break
                                    except Exception as ce:
                                        logger.debug(f"Companion augmentation notice: {ce}")
                        return res

            # Last resort: Wikipedia fallback
            wiki_res = await self._fetch_wikipedia_fallback(client, skill_name, excluded, career_title=career_title)
            if wiki_res:
                return wiki_res

        logger.warning(f"No suitable learning source found across instructional adapters for '{skill_name}'.")
        return None

    # -----------------------------------------------------------------------
    # Lesson & Quiz Synthesis (Self-Contained Micro-Lessons)
    # -----------------------------------------------------------------------

    async def atomize_and_create_quiz(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transforms raw ingested item into a self-contained micro-lesson with concept_overview,
        practice_scenario, summary_bullets, verified 5-question MCQs, and 384-d embedding.
        """
        title = raw_item.get("title", "").strip()
        skill_name = raw_item.get("skill_name", "General Skill")
        category = raw_item.get("category", "General")
        source = raw_item.get("source", "web")
        source_url = raw_item.get("source_url", "")
        raw_text = raw_item.get("raw_text", title)
        skill_id = raw_item.get("skill_id")
        career_title = raw_item.get("career_title", "Professional")

        if not title or not source_url:
            logger.warning("Skipping item with missing title or source_url")
            return None

        if not validate_source_content(raw_text, skill_name):
            logger.warning(f"Raw content for '{title}' failed sufficiency check. Aborting atomization.")
            return None

        field_meta = classify_career_field(career_title, raw_item.get("onet_soc_code"))
        field_label = field_meta["label"]
        field_directive = field_meta["extraction_directive"]

        # Select the most semantically relevant windows from long sources (instead of truncating at 3,200 chars)
        selected_evidence = await self.select_relevant_source_windows(
            raw_text=raw_text,
            skill_name=skill_name,
            career_title=career_title,
            max_chars=4200,
        )

        prompt = f"""
Career Field: {field_label}
Domain Category: {category}
Skill Target: {skill_name}
Target Career: {career_title}
Resource Title: {title}
Source: {source}

Field Pedagogical Directive:
{field_directive}

Raw Source Evidence (Strict Ground Truth — All Lesson Content & Quiz Answers MUST Derive From This Text):
---
{selected_evidence}
---

Task:
Transform this primary source evidence into a self-contained micro-learning lesson for Career Beacon.
Produce:
1. concept_overview: A clear, structured 150-220 word instructional mini-lesson synthesizing the core concepts, governing rules, calculations, or diagnostic procedures directly from the Raw Source Evidence above.
2. practice_scenario: A concrete 2-3 sentence workplace scenario showing how a {career_title} applies these exact rules or mechanisms from the Raw Source Evidence in professional decision-making.
3. summary_bullets: Exactly 3 high-yield technical takeaway bullet points (<120 words total) grounded in the Raw Source Evidence. Each bullet MUST start with '• '.
4. difficulty_level: Integer from 1 to 5 (1=Beginner, 2=Elementary, 3=Intermediate, 4=Advanced, 5=Expert).
5. quizzes: An array of EXACTLY 5 multiple-choice questions (2 conceptual, 2 workplace scenario application, 1 best-practice/pitfall).

STRICT SOURCE GROUNDING RULES:
- Every fact in concept_overview, summary_bullets, and quizzes MUST be directly supported by the Raw Source Evidence above.
- Every quiz question's correct answer and explanation MUST cite or reflect specific mechanisms, rules, or terms present in the Raw Source Evidence.
- Vary which option position holds the correct answer across questions.
"""

        system_instruction = """
You are an expert curriculum designer and psychometric assessment creator for Career Beacon.
You must return a valid JSON object matching this schema:
{
  "concept_overview": "Structured 150-220 word teaching explanation grounded in the provided source evidence...",
  "practice_scenario": "In day-to-day work, when a professional encounters...",
  "summary_bullets": "• First key concept...\\n• Second key concept...\\n• Third key concept...",
  "difficulty_level": 2,
  "quizzes": [
    {
      "question": "Clear and unambiguous question string grounded in the source text",
      "options": ["First choice", "Second choice", "Third choice", "Fourth choice"],
      "answer": "Second choice",
      "explanation": "Brief explanation citing the principle from the source text."
    }
  ]
}
Rules:
- The 'quizzes' array MUST contain EXACTLY 5 distinct questions.
- Each question MUST have exactly 4 distinct choices in 'options'.
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

        concept_overview = str(ai_data.get("concept_overview") or "").strip()
        practice_scenario = str(ai_data.get("practice_scenario") or "").strip()
        difficulty_level = safe_parse_difficulty(ai_data.get("difficulty_level"), default=2)
        quizzes = ai_data.get("quizzes", [])

        valid_quizzes = validate_quiz_structure(
            quizzes,
            source_evidence_text=f"{selected_evidence} {concept_overview} {summary_bullets}",
        )
        if not valid_quizzes:
            logger.warning(f"Quiz items failed validation for '{title}', skipping.")
            return None

        # Isomorphic pedagogical representation conforming to VECTOR_ARCHITECTURE_SPEC (25-45 words):
        # Focuses cleanly on the target skill competency, occupational category, career field, and high-yield takeaways
        # without diluting the mean-pooled vector with narrative syntax or descriptive examples.
        text_to_embed = f"Lesson: {title}. Target Skill: {skill_name} ({category}). Career Field: {field_label}. Takeaways: {summary_bullets}"
        try:
            content_vector = await self.embedding_service.get_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to compute embedding for '{title}': {e}")
            return None

        valid_uuid_skill_id: Optional[str] = None
        if skill_id:
            try:
                import uuid as _uuid_mod
                _uuid_mod.UUID(str(skill_id))
                valid_uuid_skill_id = str(skill_id)
            except Exception:
                valid_uuid_skill_id = None

        try:
            query = supabase_client.table("micro_content").select("id").eq("source_url", source_url)
            if valid_uuid_skill_id:
                query = query.eq("associated_skill_id", valid_uuid_skill_id)
            existing = query.execute()
            existing_id = existing.data[0]["id"] if (existing and existing.data) else None
        except Exception:
            existing_id = None

        trust_score = raw_item.get("trust_score") or get_source_trust_score(source)
        source_adapter = raw_item.get("source_adapter") or classify_source_adapter(source_url, source)

        content_meta = {
            "summary_bullets": summary_bullets,
            "concept_overview": concept_overview,
            "practice_scenario": practice_scenario,
            "quizzes": valid_quizzes,
            "difficulty_level": difficulty_level,
            "source_trust_score": trust_score,
            "source_name": source,
            "source_adapter": source_adapter,
            "video_id": raw_item.get("video_id"),
            "associated_skill_id": valid_uuid_skill_id or skill_id,
            "skill_name": skill_name,
            "category": category,
            "career_title": career_title,
            "field_id": field_meta["field_id"],
            "field_label": field_label,
            "source_url": source_url,
        }

        record_full = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "summary_bullets": summary_bullets,
            "content": json.dumps(content_meta),
            "associated_skill_id": valid_uuid_skill_id,
            "difficulty_level": difficulty_level,
            "source_trust_score": trust_score,
            "quizzes": valid_quizzes,
            "embedding": content_vector,
        }

        record_compat = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "content": json.dumps(content_meta),
            "embedding": content_vector,
        }

        for record_attempt in [record_full, record_compat]:
            for retry in range(2):
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
                        saved_row["concept_overview"] = concept_overview
                        saved_row["practice_scenario"] = practice_scenario
                        saved_row["source_name"] = source
                        saved_row["source_adapter"] = source_adapter
                        saved_row["video_id"] = raw_item.get("video_id")
                        return saved_row
                except Exception as e:
                    err_str = str(e)
                    if "column" in err_str and record_attempt == record_full:
                        break
                    if "disconnected" in err_str.lower() and retry == 0:
                        import time
                        time.sleep(0.5)
                        continue
                    logger.error(f"Database save error for '{title}': {e}")
                    return None

        return None

    async def generate_dynamic_lesson_for_skill(
        self,
        skill_id: str,
        skill_name: str,
        category: str = "Core",
        career_title: str = "General Career",
        target_proficiency: int = 20,
        career_skill_context: Optional[Dict[str, Any]] = None,
        preferred_adapters: Optional[List[str]] = None,
        onet_soc_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches authoritative instructional material via the 7-Adapter Pipeline,
        synthesizes a self-contained micro-lesson + 5-question checkpoint, embeds it,
        and persists to Supabase `micro_content`.
        """
        try:
            existing_res = supabase_client.table("micro_content").select("source_url").eq(
                "associated_skill_id", skill_id
            ).execute()
            excluded_urls = {row.get("source_url") for row in (existing_res.data or [])}
        except Exception:
            excluded_urls = set()

        live_source = await self.fetch_live_source_for_skill(
            skill_name,
            category,
            career_title=career_title,
            exclude_source_urls=excluded_urls,
            preferred_adapters=preferred_adapters,
            onet_soc_code=onet_soc_code,
        )
        if not live_source or not live_source.get("source_url") or not live_source.get("raw_text") or not validate_source_content(live_source.get("raw_text", ""), skill_name):
            logger.warning(f"No verifiable real educational source found for '{skill_name}' ({career_title}).")
            return None

        source_url = live_source["source_url"]
        source_title = live_source["title"]
        raw_text = live_source["raw_text"]

        title = source_title

        return await self.atomize_and_create_quiz({
            "title": title,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "category": category,
            "career_title": career_title,
            "onet_soc_code": onet_soc_code,
            "source": live_source.get("source", "Instructional Source"),
            "source_adapter": live_source.get("source_adapter"),
            "source_url": source_url,
            "raw_text": raw_text,
            "trust_score": live_source.get("trust_score"),
            "video_id": live_source.get("video_id"),
        })
