"""
backend/scripts/ingest_content.py
---------------------------------
Multi-Source Content Ingestion Worker (Zero-Key Resilient)

Fetches high-quality micro-learning content across tech and non-dev domains
(Software, Medicine, Law, Finance) without requiring external paid API keys:
  1. Dev.to API (Top developer tutorials & architecture breakdowns)
  2. StackExchange API (StackOverflow, MedicalSciences, Law, Money/Finance)
  3. Wikipedia REST API (Authoritative domain summaries & concepts)
  4. Hacker News via Algolia API (High-signal industry guides & deep-dives)
  5. YouTube Search (Keyless public query with optional YouTube API v3 upgrade)

Implements the 3-Gate Validation Pipeline:
  Gate 1: Engagement Gate (reactions >= 20, votes >= 5, points >= 30)
  Gate 2: Blacklist Gate (filters opinion pieces, rants, drama, clickbait)
  Gate 3: Tag / Skill Intersection Gate (verified match against database `skills` table)
"""

import os
import sys
import re
import html
import asyncio
from typing import List, Dict, Any, Optional
import httpx

# Ensure proper stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is on Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import supabase_client
from app.services.content_service import ContentService

# Standard User-Agent for academic and polite API requests
REQUEST_HEADERS = {
    "User-Agent": "CareerBeacon/1.0 (academic research; contact@careerbeacon.ai; polite bot)"
}

# -----------------------------------------------------------------------------
# Gate 2: Blacklist Keywords (Opinion, Rants, Subjective Drama)
# -----------------------------------------------------------------------------
BLACKLIST_PATTERNS = [
    r"\bmy thoughts on\b",
    r"\brant\b",
    r"\bwhy i left\b",
    r"\bwhy you should quit\b",
    r"\bunpopular opinion\b",
    r"\bis .* dead\b",
    r"\bi hate\b",
    r"\bdrama\b",
    r"\bcontroversial\b",
    r"\btoxic\b",
    r"\bstop using\b",
]

def passes_blacklist_gate(title: str) -> bool:
    """Gate 2: Reject opinion pieces and non-educational clickbait."""
    title_lower = title.lower()
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, title_lower):
            return False
    return True


# -----------------------------------------------------------------------------
# Domain to StackExchange Site Mapping
# -----------------------------------------------------------------------------
def get_stackexchange_site(category: Optional[str]) -> str:
    cat = (category or "").lower()
    if any(k in cat for k in ["legal", "law"]):
        return "law"
    if any(k in cat for k in ["finance", "valuation", "investment", "accounting"]):
        return "money"
    if any(k in cat for k in ["clinical", "medical", "pharmacology", "health"]):
        return "medicalsciences"
    return "stackoverflow"


# -----------------------------------------------------------------------------
# Source 1: Dev.to (Tech & Software) - ZERO KEYS REQUIRED
# -----------------------------------------------------------------------------
async def fetch_devto(client: httpx.AsyncClient, skill_name: str) -> List[Dict[str, Any]]:
    """Fetch top-rated developer articles from Dev.to API."""
    tag = re.sub(r"[^a-zA-Z0-9]", "", skill_name.lower())
    # top=30 fetches the highest engagement articles rather than 0-reaction fresh posts
    url = f"https://dev.to/api/articles?tag={tag}&top=30&per_page=10"
    candidates = []

    try:
        resp = await client.get(url, headers=REQUEST_HEADERS, timeout=10.0)
        if resp.status_code == 200:
            articles = resp.json()
            for art in articles:
                reactions = art.get("positive_reactions_count", 0)
                title = html.unescape(art.get("title", "")).strip()

                # Gate 1: Engagement Gate (> 20 reactions)
                if reactions < 20:
                    continue
                # Gate 2: Blacklist Gate
                if not passes_blacklist_gate(title):
                    continue

                desc = html.unescape(art.get("description", "") or "").strip()
                candidates.append({
                    "title": title,
                    "source": "devto",
                    "source_url": art.get("url", ""),
                    "raw_text": f"{title}. {desc}" if desc else title,
                    "engagement_metric": f"{reactions} reactions",
                    "skill_name": skill_name,
                })
    except Exception as e:
        print(f"  [Dev.to] Note for '{skill_name}': {e}")

    return candidates


# -----------------------------------------------------------------------------
# Source 2: StackExchange (Tech, Law, Medicine, Finance) - ZERO KEYS REQUIRED
# -----------------------------------------------------------------------------
async def fetch_stackexchange(client: httpx.AsyncClient, skill_name: str, category: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch high-scoring Q&A discussions from StackExchange."""
    site = get_stackexchange_site(category)
    query = re.sub(r"[^a-zA-Z0-9\s]", "", skill_name).strip()
    url = (
        f"https://api.stackexchange.com/2.3/search/advanced"
        f"?order=desc&sort=votes&q={query}&site={site}&pagesize=5&filter=default"
    )
    candidates = []

    try:
        resp = await client.get(url, headers=REQUEST_HEADERS, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", []):
                score = item.get("score", 0)
                is_answered = item.get("is_answered", False)
                title = html.unescape(item.get("title", "")).strip()

                # Gate 1: Engagement Gate (score >= 5 and verified answer)
                if score < 5 or not is_answered:
                    continue
                # Gate 2: Blacklist Gate
                if not passes_blacklist_gate(title):
                    continue

                tags = item.get("tags", [])
                candidates.append({
                    "title": title,
                    "source": f"stackexchange ({site})",
                    "source_url": item.get("link", ""),
                    "raw_text": f"{title}. Key concepts: {', '.join(tags)}",
                    "engagement_metric": f"{score} votes (accepted answer)",
                    "skill_name": skill_name,
                })
    except Exception as e:
        print(f"  [StackExchange] Note for '{skill_name}': {e}")

    return candidates


# -----------------------------------------------------------------------------
# Source 3: Wikipedia REST API (Concept Summaries) - ZERO KEYS REQUIRED
# -----------------------------------------------------------------------------
async def fetch_wikipedia(client: httpx.AsyncClient, skill_name: str, category: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch authoritative concept summaries from Wikipedia REST API."""
    candidates = []
    headers = {"User-Agent": "CareerBeacon/1.0 (academic research; contact@careerbeacon.ai)"}

    # Potential title candidates for Wikipedia
    slugs_to_try = [skill_name.strip().replace(" ", "_")]
    if category and "program" in category.lower():
        slugs_to_try.append(f"{skill_name.strip()}_(programming_language)".replace(" ", "_"))

    for slug in slugs_to_try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
        try:
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "")
                extract = data.get("extract", "")
                page_type = data.get("type", "")

                # Gate 1: Meaningful educational extract (> 80 characters, standard article)
                if page_type == "standard" and len(extract) > 80:
                    if passes_blacklist_gate(title):
                        candidates.append({
                            "title": f"Fundamentals of {title}",
                            "source": "wikipedia",
                            "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "raw_text": extract,
                            "engagement_metric": "Verified Encyclopaedia Entry",
                            "skill_name": skill_name,
                        })
                        break  # Found high-quality match
        except Exception as e:
            print(f"  [Wikipedia] Note for '{skill_name}': {e}")

    return candidates


# -----------------------------------------------------------------------------
# Source 4: Hacker News (Algolia Search) - ZERO KEYS REQUIRED
# -----------------------------------------------------------------------------
async def fetch_hackernews(client: httpx.AsyncClient, skill_name: str) -> List[Dict[str, Any]]:
    """Fetch high-scoring tutorials, deep-dives, and guides from Hacker News Algolia."""
    query = f"{skill_name} tutorial guide"
    url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=5"
    candidates = []

    try:
        resp = await client.get(url, headers=REQUEST_HEADERS, timeout=10.0)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                points = hit.get("points") or 0
                title = html.unescape(hit.get("title", "")).strip()
                item_url = hit.get("url")

                # Gate 1: Engagement Gate (>= 30 community upvotes)
                if points < 30 or not item_url:
                    continue
                # Gate 2: Blacklist Gate
                if not passes_blacklist_gate(title):
                    continue

                candidates.append({
                    "title": title,
                    "source": "hackernews",
                    "source_url": item_url,
                    "raw_text": f"{title}. Community discussion: {points} points on Hacker News.",
                    "engagement_metric": f"{points} HN upvotes",
                    "skill_name": skill_name,
                })
    except Exception as e:
        print(f"  [HackerNews] Note for '{skill_name}': {e}")

    return candidates


# -----------------------------------------------------------------------------
# Source 5: YouTube (Video Lessons) - ZERO KEYS REQUIRED (Fallback Supported)
# -----------------------------------------------------------------------------
async def fetch_youtube(client: httpx.AsyncClient, skill_name: str) -> List[Dict[str, Any]]:
    """Fetch educational videos. Upgrades to YouTube API v3 if key exists, otherwise keyless search."""
    candidates = []

    # Scenario A: Official YouTube API v3 (if key is configured)
    if settings.youtube_api_key:
        query = f"{skill_name} educational lesson tutorial"
        url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={query}&type=video&maxResults=5&key={settings.youtube_api_key}"
        )
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    title = html.unescape(snippet.get("title", "")).strip()
                    video_id = item.get("id", {}).get("videoId", "")
                    channel_title = snippet.get("channelTitle", "")

                    if not passes_blacklist_gate(title):
                        continue

                    candidates.append({
                        "title": title,
                        "source": "youtube",
                        "source_url": f"https://www.youtube.com/watch?v={video_id}",
                        "raw_text": f"{title}. Channel: {channel_title}. {html.unescape(snippet.get('description', ''))}",
                        "engagement_metric": f"Channel: {channel_title}",
                        "skill_name": skill_name,
                    })
                return candidates
        except Exception as e:
            print(f"  [YouTube API] Error: {e}, falling back to zero-key search...")

    # Scenario B: Zero-Key YouTube Public Search Fallback
    try:
        search_query = f"{skill_name} full tutorial course lesson"
        url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=10.0)
        if resp.status_code == 200:
            video_ids = list(dict.fromkeys(re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", resp.text)))
            raw_titles = list(dict.fromkeys(re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}\]', resp.text)))

            for vid, raw_t in zip(video_ids[:3], raw_titles[:3]):
                clean_title = html.unescape(raw_t).strip()
                if not clean_title or len(clean_title) < 5 or not passes_blacklist_gate(clean_title):
                    continue

                candidates.append({
                    "title": clean_title,
                    "source": "youtube (video)",
                    "source_url": f"https://www.youtube.com/watch?v={vid}",
                    "raw_text": f"Video tutorial: {clean_title} covering core competencies in {skill_name}.",
                    "engagement_metric": "Public Video Lecture",
                    "skill_name": skill_name,
                })
    except Exception as e:
        print(f"  [YouTube Keyless] Note for '{skill_name}': {e}")

    return candidates


# -----------------------------------------------------------------------------
# Worker Orchestrator
# -----------------------------------------------------------------------------
async def run_ingestion_for_skills(target_skills: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Main worker loop:
      1. Load skills from database for Gate 3 validation reference
      2. Concurrently poll all zero-key sources
      3. Filter through Gates 1, 2, and 3
      4. Deduplicate entries by source_url
    """
    print("\n=======================================================")
    print("   CAREER BEACON - CONTENT INGESTION WORKER (ZERO-KEY) ")
    print("=======================================================\n")

    # Gate 3 Reference: Load existing skills from Supabase (with retry for transient drops)
    db_skills = []
    for attempt in range(1, 4):
        try:
            db_skills_res = supabase_client.table("skills").select("id, name, category").execute()
            db_skills = db_skills_res.data or []
            break
        except Exception as e:
            if attempt < 3:
                await asyncio.sleep(1.0)
            else:
                print(f"Warning: Could not fetch skills from Supabase: {e}")

    db_skill_names = {s["name"].lower(): s for s in db_skills}

    print(f"Loaded {len(db_skills)} reference skills from database for Gate 3 validation.")

    skills_to_process = target_skills if target_skills else db_skills[:10]
    print(f"Processing ingestion for {len(skills_to_process)} target skills...\n")

    all_accepted: List[Dict[str, Any]] = []
    seen_urls = set()

    async with httpx.AsyncClient(timeout=12.0) as client:
        for skill in skills_to_process:
            s_name = skill["name"]
            s_cat = skill.get("category", "")
            print(f"-> Processing Skill: '{s_name}' [{s_cat}]")

            # Concurrently poll all 5 sources (all zero-key friendly)
            tasks = [
                fetch_devto(client, s_name),
                fetch_stackexchange(client, s_name, s_cat),
                fetch_wikipedia(client, s_name, s_cat),
                fetch_hackernews(client, s_name),
                fetch_youtube(client, s_name),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            raw_candidates: List[Dict[str, Any]] = []
            for res in results:
                if isinstance(res, list):
                    raw_candidates.extend(res)

            # Gate 3: Tag / Skill Intersection Gate & URL deduplication
            passed_gate3 = 0
            for item in raw_candidates:
                url = item.get("source_url")
                if not url or url in seen_urls:
                    continue

                matched_skill = db_skill_names.get(item["skill_name"].lower())
                if matched_skill:
                    seen_urls.add(url)
                    item["skill_id"] = matched_skill["id"]
                    item["category"] = matched_skill.get("category", "")
                    all_accepted.append(item)
                    passed_gate3 += 1
                    print(f"   [PASSED 3 GATES] {item['source']:<22} | {item['title'][:42]}... ({item['engagement_metric']})")

            if passed_gate3 == 0:
                print("   (No candidate content passed all 3 gates for this skill)")

    print(f"\n=======================================================")
    print(f" Ingestion Run Complete: {len(all_accepted)} unique items validated across all 3 gates.")
    print("=======================================================\n")
    return all_accepted


async def ingest_and_atomize_pipeline(
    target_skills: Optional[List[Dict[str, Any]]] = None,
    max_per_skill: int = 2
) -> List[Dict[str, Any]]:
    """
    Complete Pipeline (Task 6.1 + Task 6.2):
      1. Ingest across multi-sources through 3 gates
      2. Condense into 3-bullet takeaways
      3. Generate 5-question MCQ JSON array
      4. Compute 384-dim vector embeddings
      5. Persist to Supabase `micro_content` table
    """
    validated_items = await run_ingestion_for_skills(target_skills)

    print("\n=======================================================")
    print("   TASK 6.2: CONTENT ATOMIZATION & 5-MCQ GENERATION    ")
    print("=======================================================\n")

    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    for item in validated_items:
        by_skill.setdefault(item["skill_name"], []).append(item)

    content_service = ContentService()
    saved_lessons: List[Dict[str, Any]] = []

    for s_name, items in by_skill.items():
        print(f"\n-> Atomizing lessons for skill: '{s_name}' (Target: {min(len(items), max_per_skill)} lessons)")
        for item in items[:max_per_skill]:
            print(f"   [LLM Processing] '{item['title'][:50]}...'")
            saved = await content_service.atomize_and_create_quiz(item)
            if saved:
                saved_lessons.append(saved)
                lesson_id = saved.get("id", "OK")
                quiz_count = len(saved.get("quizzes", []))
                print(f"   [COMMITTED] Lesson ID: {lesson_id} | Quizzes: {quiz_count} MCQs | Difficulty: {saved.get('difficulty_level')}")
            else:
                print(f"   [SKIPPED] Could not process '{item['title'][:40]}'")

    print(f"\n=======================================================")
    print(f" Pipeline Complete: {len(saved_lessons)} lessons atomized and persisted to Supabase.")
    print("=======================================================\n")
    return saved_lessons


if __name__ == "__main__":
    # Representative cross-domain skills (Tech + Medical + Legal + Finance)
    test_sample = [
        {"name": "Python", "category": "Programming"},
        {"name": "Pharmacology", "category": "Medical Science"},
        {"name": "Contract Drafting", "category": "Legal"},
        {"name": "Financial Modelling", "category": "Finance"},
    ]
    # Run full ingestion + atomization + 5-question quiz generation pipeline!
    asyncio.run(ingest_and_atomize_pipeline(test_sample, max_per_skill=1))

