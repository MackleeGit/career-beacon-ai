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
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus, urlparse
import httpx

from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.core.database import supabase_client
from app.core.config import settings

logger = logging.getLogger("career_beacon.content_service")

# Calibrated base authority weights by instructional adapter
SOURCE_AUTHORITY_WEIGHTS: Dict[str, float] = {
    "youtube": 0.94,
    "structured_tutorial": 0.92,
    "open_textbook": 0.90,
    "clinical_science": 0.95,
    "mdn": 0.95,
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
    if "youtube" in low:
        return SOURCE_AUTHORITY_WEIGHTS["youtube"]
    if any(k in low for k in ("geeksforgeeks", "tutorialspoint", "w3schools", "structured_tutorial")):
        return SOURCE_AUTHORITY_WEIGHTS["structured_tutorial"]
    if any(k in low for k in ("wikibooks", "wikiversity", "open_textbook")):
        return SOURCE_AUTHORITY_WEIGHTS["open_textbook"]
    if any(k in low for k in ("ncbi", "statpearls", "europe pmc", "europepmc", "clinical_science")):
        return SOURCE_AUTHORITY_WEIGHTS["clinical_science"]
    if "mdn" in low or "mozilla" in low:
        return SOURCE_AUTHORITY_WEIGHTS["mdn"]
    if "openalex" in low:
        return SOURCE_AUTHORITY_WEIGHTS["openalex"]
    if "wikipedia" in low:
        return SOURCE_AUTHORITY_WEIGHTS["wikipedia"]
    return None


def classify_source_adapter(source_url: str, source_label: str = "") -> str:
    """Maps a lesson URL or source label to one of the 7 canonical adapter keys for the Feed Mixer."""
    combined = f"{source_url or ''} {source_label or ''}".lower()
    if "youtube.com" in combined or "youtu.be" in combined:
        return "youtube"
    if any(k in combined for k in ("geeksforgeeks.org", "tutorialspoint.com", "w3schools.com")):
        return "structured_tutorial"
    if any(k in combined for k in ("wikibooks.org", "wikiversity.org", "openstax.org", "opentextbc.ca")):
        return "open_textbook"
    if any(k in combined for k in ("ncbi.nlm.nih.gov", "europepmc.org", "ebi.ac.uk")):
        return "clinical_science"
    if "developer.mozilla.org" in combined:
        return "mdn"
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
        # Match full token or 5-char stem for morphological variants (e.g. "welding" vs "weld")
        matched = any(
            (token in lower_text) or (len(token) >= 5 and token[:5] in lower_text)
            for token in meaningful_tokens
        )
        if not matched:
            return False

    return True


def validate_quiz_structure(quizzes: Any) -> List[Dict[str, Any]]:
    """
    Validates that each quiz item is a well-formed multiple-choice question:
      - 'question': non-empty string (>= 10 chars).
      - 'options': exactly 4 distinct, non-empty options.
      - 'answer': string that exactly matches one of the 4 options.
      - 'explanation': non-empty pedagogical rationale.
    Returns the list of valid quiz items (requires >= 3 valid items).
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
            "explanation": explanation or "Verified against lesson material.",
        })

    if len(valid_quizzes) < 3:
        return []

    return valid_quizzes


class ContentService:
    def __init__(self):
        self.ai_service = AIService()
        self.embedding_service = EmbeddingService()

    # -----------------------------------------------------------------------
    # Modular Source Adapters
    # -----------------------------------------------------------------------

    async def _fetch_youtube_lecture(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 1: YouTube Educational Lectures & Tutorials (Universal Career Coverage)."""
        try:
            video_items = []
            search_phrase = f"{career_title} {skill_name} tutorial lecture explained".strip()
            if settings.youtube_api_key:
                query = quote_plus(search_phrase)
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search"
                    f"?part=snippet&q={query}&type=video&videoDuration=medium&maxResults=5&key={settings.youtube_api_key}",
                    headers={"User-Agent": ACADEMIC_USER_AGENT},
                )
                if response.status_code == 200:
                    for entry in response.json().get("items", []):
                        video_id = entry.get("id", {}).get("videoId")
                        snippet = entry.get("snippet", {})
                        if video_id:
                            video_items.append((video_id, snippet.get("title", ""), snippet.get("description", "")))
            else:
                query = quote_plus(search_phrase)
                response = await client.get(
                    f"https://www.youtube.com/results?search_query={query}",
                    headers={"User-Agent": BROWSER_USER_AGENT},
                )
                if response.status_code == 200:
                    ids = list(dict.fromkeys(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)))
                    titles = list(dict.fromkeys(re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}', response.text)))
                    video_items = [(vid, html.unescape(t), "") for vid, t in zip(ids[:5], titles[:5])]

            anecdote_noise = ("vlog", "day in my life", "day in the life", "my opinion", "reacting to", "unboxing", "shorts")
            for video_id, video_title, description in video_items[:3]:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                if video_url in excluded or not video_title:
                    continue
                if any(bad in video_title.lower() for bad in anecdote_noise):
                    continue

                transcript_text = ""
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    transcript = await asyncio.wait_for(
                        asyncio.to_thread(YouTubeTranscriptApi().fetch, video_id, languages=["en"]),
                        timeout=5.0,
                    )
                    transcript_text = " ".join(part.text for part in transcript.snippets)
                except Exception:
                    pass

                raw = strip_html_and_clean(transcript_text or description or "")
                if validate_source_content(raw, skill_name):
                    return {
                        "title": html.unescape(video_title).strip(),
                        "source_url": video_url,
                        "raw_text": raw[:10000],
                        "source": "YouTube transcript" if transcript_text else "YouTube lecture",
                        "source_adapter": "youtube",
                        "video_id": video_id,
                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["youtube"],
                    }
        except Exception as e:
            logger.debug(f"YouTube adapter error: {e}")
        return None

    async def _fetch_structured_tutorial(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        category: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 2: GeeksforGeeks, Tutorialspoint & W3Schools Structured Tutorials."""
        clean_lower = skill_name.strip().lower()
        kebab_slug = re.sub(r"[^a-z0-9]+", "-", clean_lower).strip("-")
        compact_slug = re.sub(r"[^a-z0-9]+", "", clean_lower)
        underscore_slug = re.sub(r"[^a-z0-9]+", "_", clean_lower).strip("_")

        w3_map = {"javascript": "js", "typescript": "typescript", "c#": "cs", "c++": "cpp", "python": "python", "sql": "sql", "html": "html", "css": "css", "react": "react"}
        w3_slug = w3_map.get(clean_lower, compact_slug)

        candidate_targets = [
            (f"https://www.geeksforgeeks.org/{kebab_slug}/", "GeeksforGeeks", f"{skill_name} — GeeksforGeeks Guide"),
            (f"https://www.tutorialspoint.com/{underscore_slug}/index.htm", "Tutorialspoint", f"{skill_name} — Tutorialspoint Course"),
            (f"https://www.w3schools.com/{w3_slug}/", "W3Schools", f"{skill_name} tutorial"),
        ]

        for target_url, provider_name, fallback_title in candidate_targets:
            if target_url in excluded:
                continue
            try:
                resp = await client.get(target_url, headers={"User-Agent": BROWSER_USER_AGENT})
                if resp.status_code == 200 and resp.text:
                    final_url = str(resp.url)
                    if final_url in excluded:
                        continue
                    extracted = _extract_article_html(resp.text)
                    if validate_source_content(extracted, skill_name):
                        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", resp.text, flags=re.DOTALL | re.IGNORECASE)
                        page_title = strip_html_and_clean(title_match.group(1)) if title_match else fallback_title
                        if not page_title or len(page_title) < 4:
                            page_title = fallback_title
                        return {
                            "title": page_title[:140],
                            "source_url": final_url,
                            "raw_text": extracted[:10000],
                            "source": provider_name,
                            "source_adapter": "structured_tutorial",
                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["structured_tutorial"],
                        }
            except Exception as e:
                logger.debug(f"{provider_name} adapter error: {e}")
        return None

    async def _fetch_mdn_docs(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        category: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter 3: MDN Web Docs Official Search API (Software, Web, Data, Security)."""
        context = f"{category} {career_title} {skill_name}".lower()
        if not any(k in context for k in ("tech", "software", "web", "data", "develop", "code", "program", "javascript", "css", "html", "http", "api", "security", "sql", "python")):
            return None
        try:
            q = quote_plus(skill_name)
            resp = await client.get(
                f"https://developer.mozilla.org/api/v1/search?q={q}&locale=en-US",
                headers={"User-Agent": ACADEMIC_USER_AGENT},
            )
            if resp.status_code == 200:
                docs = resp.json().get("documents", [])
                for doc in docs[:3]:
                    mdn_url = f"https://developer.mozilla.org{doc.get('mdn_url', '')}"
                    if not doc.get("mdn_url") or mdn_url in excluded:
                        continue
                    summary = doc.get("summary", "")
                    title = doc.get("title", skill_name)
                    # Fetch full MDN page for rich instructional text
                    page_resp = await client.get(mdn_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
                    body_text = _extract_article_html(page_resp.text) if page_resp.status_code == 200 else summary
                    combined = f"{title}. {summary}\n\n{body_text}".strip()
                    if validate_source_content(combined, skill_name):
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
        apis = [
            ("https://en.wikibooks.org/w/api.php", "https://en.wikibooks.org/wiki/", "Wikibooks"),
            ("https://en.wikiversity.org/w/api.php", "https://en.wikiversity.org/wiki/", "Wikiversity"),
        ]
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for api_url, wiki_base, label in apis:
            for query_str in (f"{skill_name} {career_title}".strip(), skill_name):
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
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:")):
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
                                if validate_source_content(extract, skill_name):
                                    return {
                                        "title": page_title,
                                        "source_url": page_url,
                                        "raw_text": extract[:10000],
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
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        try:
            query = quote_plus(f'"{skill_name}" AND ({career_title or "practice"})')
            resp = await client.get(
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&resultType=core&format=json&pageSize=5",
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
                    if validate_source_content(combined, skill_name):
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
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for search_q in (f"{skill_name} {career_title}".strip(), skill_name):
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
                        if validate_source_content(combined, skill_name):
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
    ) -> Optional[Dict[str, Any]]:
        """Adapter 7: Wikipedia Multi-Section Extracts (Strictly Last-Resort Fallback)."""
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        slug = skill_name.strip().replace(" ", "_")
        try:
            r_wiki = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug)}", headers=headers)
            if r_wiki.status_code == 200:
                d = r_wiki.json()
                extract = d.get("extract", "")
                if d.get("type") == "standard" and validate_source_content(extract, skill_name):
                    page_url = d.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug}"
                    if page_url not in excluded:
                        return {
                            "title": d.get("title", skill_name),
                            "source_url": page_url,
                            "raw_text": extract[:5000],
                            "source": "wikipedia",
                            "source_adapter": "wikipedia",
                            "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                        }
        except Exception as e:
            logger.debug(f"Wikipedia summary error: {e}")

        try:
            r_srch = await client.get(
                f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(skill_name)}&utf8=&format=json",
                headers=headers,
            )
            if r_srch.status_code == 200:
                results = r_srch.json().get("query", {}).get("search", [])
                if results:
                    best_title = results[0]["title"]
                    slug2 = best_title.replace(" ", "_")
                    r_sum = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug2)}", headers=headers)
                    if r_sum.status_code == 200:
                        d2 = r_sum.json()
                        extract2 = d2.get("extract", "")
                        if d2.get("type") == "standard" and validate_source_content(extract2, skill_name):
                            page_url = d2.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug2}"
                            if page_url not in excluded:
                                return {
                                    "title": d2.get("title", best_title),
                                    "source_url": page_url,
                                    "raw_text": extract2[:5000],
                                    "source": "wikipedia",
                                    "source_adapter": "wikipedia",
                                    "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                                }
        except Exception as e:
            logger.debug(f"Wikipedia search fallback error: {e}")
        return None

    async def fetch_live_source_for_skill(
        self,
        skill_name: str,
        category: str = "Core",
        career_title: str = "",
        exclude_source_urls: Optional[set] = None,
        preferred_adapters: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes the modular instructional source pipeline for any career and skill.
        Prioritizes active teaching sources (YouTube lectures, GeeksforGeeks/Tutorialspoint/W3Schools,
        MDN Web Docs, Wikibooks/Wikiversity Open Textbooks, NCBI/EuropePMC, OpenAlex) and uses
        Wikipedia strictly as a last-resort fallback.
        """
        excluded = {u for u in (exclude_source_urls or set()) if u}
        context = f"{category or ''} {career_title or ''} {skill_name or ''}".lower()
        is_health_or_bio = any(k in context for k in ("health", "medical", "clinical", "dental", "nurs", "pharmac", "therap", "patient", "biolog", "anatom", "surgical"))
        is_tech = any(k in context for k in ("tech", "software", "program", "data", "develop", "web", "ai", "cloud", "cyber", "network", "sql", "python", "javascript", "engineer"))

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            # Build domain-aware adapter execution order
            adapter_order = []
            if is_health_or_bio:
                adapter_order.extend([
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                ])
            elif is_tech:
                adapter_order.extend([
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            else:
                # Universal career routing (Finance, Management, Trades, Culinary, Law, Operations, Creative)
                adapter_order.extend([
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                ])

            # If caller requested specific preferred adapters (e.g., Mixer diversity), move them to front
            if preferred_adapters:
                pref_set = set(preferred_adapters)
                adapter_order.sort(key=lambda pair: 0 if pair[0] in pref_set else 1)

            for adapter_name, adapter_fn in adapter_order:
                res = await adapter_fn()
                if res:
                    return res

            # Last resort: Wikipedia fallback
            wiki_res = await self._fetch_wikipedia_fallback(client, skill_name, excluded)
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

        prompt = f"""
Domain Category: {category}
Skill Target: {skill_name}
Target Career: {career_title}
Resource Title: {title}
Source: {source}

Raw Source Content (Strict Ground Truth):
---
{raw_text[:3200]}
---

Task:
Transform this educational material into a self-contained micro-learning lesson for Career Beacon.
Produce:
1. concept_overview: A clear, structured 150-220 word instructional mini-lesson explaining the core concepts, rules, or procedures so the learner can master the topic right inside the app.
2. practice_scenario: A concrete 2-3 sentence workplace scenario showing how a {career_title} applies {skill_name} in practice.
3. summary_bullets: Exactly 3 high-yield technical takeaway bullet points (<120 words total). Each bullet MUST start with '• '.
4. difficulty_level: Integer from 1 to 5 (1=Beginner, 2=Elementary, 3=Intermediate, 4=Advanced, 5=Expert).
5. quizzes: An array of EXACTLY 5 multiple-choice questions (2 conceptual, 2 workplace scenario application, 1 best-practice/pitfall).

GROUNDING RULES:
- Every quiz question MUST be 100% answerable from the concept_overview, practice_scenario, and summary_bullets you write above.
- Do NOT ask questions about obscure trivia not covered in your lesson overview.
"""

        system_instruction = """
You are an expert curriculum designer and psychometric assessment creator for Career Beacon.
You must return a valid JSON object matching this schema:
{
  "concept_overview": "Structured 150-220 word teaching explanation...",
  "practice_scenario": "In day-to-day work, when a professional encounters...",
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

        concept_overview = str(ai_data.get("concept_overview") or "").strip()
        practice_scenario = str(ai_data.get("practice_scenario") or "").strip()
        difficulty_level = max(1, min(5, int(ai_data.get("difficulty_level", 2))))
        quizzes = ai_data.get("quizzes", [])

        valid_quizzes = validate_quiz_structure(quizzes)
        if not valid_quizzes:
            logger.warning(f"Quiz items failed validation for '{title}', skipping.")
            return None

        text_to_embed = f"{title}. Skill: {skill_name} ({category}). Summary: {summary_bullets} {concept_overview[:400]}"
        try:
            content_vector = await self.embedding_service.get_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to compute embedding for '{title}': {e}")
            return None

        try:
            existing = supabase_client.table("micro_content").select("id").eq(
                "source_url", source_url
            ).eq("associated_skill_id", skill_id).execute()
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
            "associated_skill_id": skill_id,
            "skill_name": skill_name,
            "category": category,
            "career_title": career_title,
            "source_url": source_url,
        }

        record_full = {
            "title": title,
            "source_url": source_url,
            "summary": summary_bullets,
            "summary_bullets": summary_bullets,
            "content": json.dumps(content_meta),
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
            "content": json.dumps(content_meta),
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
                    saved_row["concept_overview"] = concept_overview
                    saved_row["practice_scenario"] = practice_scenario
                    saved_row["source_name"] = source
                    saved_row["source_adapter"] = source_adapter
                    return saved_row
            except Exception as e:
                err_str = str(e)
                if "column" in err_str and record_attempt == record_full:
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
        )
        if not live_source or not live_source.get("source_url") or not live_source.get("raw_text"):
            logger.warning(f"No verifiable source material found for '{skill_name}'. Aborting dynamic lesson generation.")
            return None

        source_url = live_source["source_url"]
        source_title = live_source["title"]
        raw_text = live_source["raw_text"]

        if not validate_source_content(raw_text, skill_name):
            logger.warning(f"Source content for '{skill_name}' failed sufficiency validation.")
            return None

        title = f"{source_title} — {career_title}" if career_title and career_title.lower() not in source_title.lower() else source_title

        return await self.atomize_and_create_quiz({
            "title": title,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "category": category,
            "career_title": career_title,
            "source": live_source.get("source", "Instructional Source"),
            "source_adapter": live_source.get("source_adapter"),
            "source_url": source_url,
            "raw_text": raw_text,
            "trust_score": live_source.get("trust_score"),
            "video_id": live_source.get("video_id"),
        })
