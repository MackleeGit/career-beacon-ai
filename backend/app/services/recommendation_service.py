"""
----------------------------------------------
Two-Stage Hybrid Recommendation Engine


Architecture:
  STAGE 1: DATABASE COARSE FILTER (Supabase / pgvector)
    - Constructs user skill-gap frontier embedding.
    - Uses pgvector cosine similarity (<=>) to retrieve top 30 candidate items.
    - Gracefully falls back to relational fetch if stored procedure is pending.

  STAGE 2: PYTHON RE-RANKING ENGINE (FastAPI / Graph Weights)
    - Priority in Difficulty: Penalizes high-difficulty content for low-proficiency nodes.
    - Career Context: Carries occupation and O*NET/ESCO skill metadata into retrieval.
    - Source Diversity: Retrieves additional validated sources when a skill has only one domain.
    - Sorts and delivers final Top 5 micro-learning feed.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.content_service import ContentService
from app.services.learning_history_service import LearningHistoryService, ATTEMPTS_FILE, ACTIVITY_FILE

logger = logging.getLogger("career_beacon.recommendation_service")


def _normalized_career_label(value: str) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9]+", (value or "").lower())
    normalized = []
    for word in words:
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        normalized.append(word)
    return tuple(normalized)


def _explicit_lesson_career(item: Dict[str, Any]) -> Optional[str]:
    """Read explicit career attribution from stored metadata or generated title."""
    career_title = item.get("career_title")
    content = item.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (TypeError, ValueError):
            content = None
    if not career_title and isinstance(content, dict):
        career_title = content.get("career_title")

    if career_title and str(career_title).strip():
        return str(career_title).strip()

    title = item.get("title") or ""
    match = re.search(r"\bFundamentals for\s+(.+?)\s*$", title, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _lesson_matches_career(item: Dict[str, Any], career_title: str) -> bool:
    """Keep generic lessons, but reject lessons explicitly made for another career."""
    lesson_career = _explicit_lesson_career(item)
    if not lesson_career:
        return True
    expected = _normalized_career_label(career_title)
    actual = _normalized_career_label(lesson_career)
    return not expected or actual == expected


SOC_MAJOR_GROUP_DOMAINS: Dict[str, str] = {
    "11": "business_admin",     # Management Occupations
    "13": "business_finance",   # Business and Financial Operations
    "15": "tech",               # Computer and Mathematical
    "17": "engineering",        # Architecture and Engineering
    "19": "science",            # Life, Physical, and Social Science
    "21": "social_services",    # Community and Social Service
    "23": "legal",              # Legal Occupations
    "25": "education",          # Educational Instruction and Library
    "27": "creative_media",     # Arts, Design, Entertainment, Sports, and Media
    "29": "healthcare",         # Healthcare Practitioners and Technical
    "31": "healthcare",         # Healthcare Support
    "33": "protective_service", # Protective Service Occupations
    "35": "hospitality_food",   # Food Preparation and Serving
    "37": "facility_maintenance", # Building and Grounds Cleaning/Maintenance
    "39": "personal_care",      # Personal Care and Service
    "41": "business_finance",   # Sales and Related
    "43": "business_admin",     # Office and Administrative Support
    "45": "trades_industrial",  # Farming, Fishing, and Forestry
    "47": "trades_industrial",  # Construction and Extraction
    "49": "trades_industrial",  # Installation, Maintenance, and Repair
    "51": "trades_industrial",  # Production Occupations
    "53": "transportation",     # Transportation and Material Moving
    "55": "military",           # Military Specific Occupations
}

RESTRICTED_ADAPTER_DOMAINS: Dict[str, set] = {
    "clinical_science": {"healthcare", "science"},
    "mdn": {"tech"},
    "owasp": {"tech", "protective_service"},
    "osha": {"trades_industrial", "engineering", "healthcare", "transportation"},
    "finance": {"business_finance", "business_admin"},
}


def resolve_career_domain_standard(career_title: str, onet_soc_code: Optional[str] = None) -> str:
    """
    Standard BLS SOC taxonomy domain resolution.
    1. Checks the 2-digit Major Group prefix if onet_soc_code is present.
    2. Fallback for the ~15 non-standard or custom AI occupations.
    """
    if onet_soc_code:
        prefix = str(onet_soc_code).strip()[:2]
        if prefix in SOC_MAJOR_GROUP_DOMAINS:
            return SOC_MAJOR_GROUP_DOMAINS[prefix]

    title_low = (career_title or "").lower()
    if any(k in title_low for k in ("health", "medic", "dent", "doctor", "nurs", "physic", "pharm", "therap", "surg", "clinical")):
        return "healthcare"
    if any(k in title_low for k in ("software", "develop", "program", "data", "web", "computer", "cloud", "devops", "cyber", "ai")):
        return "tech"
    if any(k in title_low for k in ("engineer", "aerospace", "mechanical", "electrical", "civil", "architect")):
        return "engineering"
    if any(k in title_low for k in ("secretar", "administrat", "office", "clerk", "reception", "assistant", "coordinator")):
        return "business_admin"
    if any(k in title_low for k in ("finance", "account", "bank", "invest", "audit", "tax", "budget")):
        return "business_finance"
    if any(k in title_low for k in ("pilot", "flight", "driver", "transport", "aviation", "maritime", "cargo")):
        return "transportation"
    if any(k in title_low for k in ("welder", "plumb", "electrician", "carpent", "mechanic", "machin", "construct")):
        return "trades_industrial"
    return "general"


def _is_adapter_compatible_with_career(item: Dict[str, Any], career_title: str, onet_soc_code: Optional[str] = None) -> bool:
    """Taxonomy-driven adapter capability gate across all 855 careers."""
    adapter = (item.get("source_adapter") or "").lower()
    url = (item.get("source_url") or "").lower()
    if not adapter:
        if "developer.mozilla.org" in url or "w3schools.com" in url or "geeksforgeeks.org" in url:
            adapter = "mdn"
        elif "europepmc.org" in url or "ncbi.nlm.nih.gov" in url or "pubmed" in url:
            adapter = "clinical_science"
        elif "owasp.org" in url:
            adapter = "owasp"
        elif "osha.gov" in url:
            adapter = "osha"

    domain = resolve_career_domain_standard(career_title, onet_soc_code)
    allowed_domains = RESTRICTED_ADAPTER_DOMAINS.get(adapter)
    if allowed_domains is not None and domain not in allowed_domains:
        return False
    return True


def _filter_candidates_for_career(items: List[Dict[str, Any]], career_title: str) -> List[Dict[str, Any]]:
    """Drop cross-career lessons, domain-incompatible adapters, and generic/Wikipedia copies when better-fit material exists."""
    career_items = [
        item for item in items
        if _lesson_matches_career(item, career_title) and _is_adapter_compatible_with_career(item, career_title)
    ]
    career_specific_skills = {
        item.get("associated_skill_id")
        for item in career_items
        if item.get("associated_skill_id") and _explicit_lesson_career(item)
    }
    non_wiki_skills = set()
    for item in career_items:
        skill_id = item.get("associated_skill_id")
        host = (urlparse(item.get("source_url") or "").hostname or "").lower()
        if skill_id and host not in {"wikipedia.org", "www.wikipedia.org"}:
            non_wiki_skills.add(skill_id)

    filtered = []
    for item in career_items:
        skill_id = item.get("associated_skill_id")
        explicit_career = bool(_explicit_lesson_career(item))
        host = (urlparse(item.get("source_url") or "").hostname or "").lower()
        is_wikipedia = host == "wikipedia.org" or host.endswith(".wikipedia.org")
        if skill_id in career_specific_skills and not explicit_career:
            continue
        if is_wikipedia and skill_id in non_wiki_skills:
            continue
        filtered.append(item)
    return filtered


def _source_quality_multiplier(item: Dict[str, Any], career_title: str) -> float:
    """Weight instructional sources by pedagogical depth; strongly demote Wikipedia fallback."""
    url = item.get("source_url") or ""
    host = (urlparse(url).hostname or "").lower()
    explicit_career = _explicit_lesson_career(item)
    if host == "wikipedia.org" or host.endswith(".wikipedia.org"):
        return 0.50

    high_instructional = any(
        domain in host
        for domain in (
            "youtube.com", "youtu.be", "geeksforgeeks.org", "tutorialspoint.com",
            "w3schools.com", "developer.mozilla.org", "wikibooks.org", "wikiversity.org",
            "ncbi.nlm.nih.gov", "europepmc.org", "openstax.org", "opentextbc.ca", "nptel.ac.in",
        )
    ) or host.endswith((".edu", ".ac.uk", ".ac.in"))

    matches_career = bool(
        explicit_career
        and _normalized_career_label(explicit_career) == _normalized_career_label(career_title)
    )
    if high_instructional:
        return 1.15 if matches_career else 1.10
    if matches_career:
        return 1.05
    return 0.92 if not explicit_career else 1.0


def _apply_feed_mixer(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    3-Step Anti-Clog Feed Mixer:
      1. Caps Wikipedia fallback at max 1 item per sprint (and 0 if primary instructional sources fill the batch).
      2. Caps any single source adapter at max ceil(limit * 0.45) when other adapters are available.
      3. Interleaves items so back-to-back cards vary across skills and sources while preserving rank order.
    """
    if len(items) <= 2:
        return items[:limit]

    non_wiki = [it for it in items if it.get("source_adapter") != "wikipedia"]
    wiki_only = [it for it in items if it.get("source_adapter") == "wikipedia"]

    # Only allow at most 1 Wikipedia fallback card if non-Wikipedia items cannot fill `limit`
    pool = list(non_wiki)
    if len(pool) < limit and wiki_only:
        pool.append(wiki_only[0])
    if len(pool) < limit and len(wiki_only) > 1:
        pool.extend(wiki_only[1 : limit - len(pool) + 1])

    # Greedy round-robin interleaving to avoid consecutive duplicate skill_id or source_adapter
    mixed: List[Dict[str, Any]] = []
    remaining = list(pool)
    while remaining and len(mixed) < limit:
        if not mixed:
            mixed.append(remaining.pop(0))
            continue
        prev_skill = mixed[-1].get("associated_skill_id")
        prev_adapter = mixed[-1].get("source_adapter")

        # Find highest-ranked item that differs in skill (and ideally source adapter)
        best_idx = 0
        for idx, cand in enumerate(remaining):
            diff_skill = cand.get("associated_skill_id") != prev_skill
            diff_adapter = cand.get("source_adapter") != prev_adapter
            if diff_skill and diff_adapter:
                best_idx = idx
                break
            if diff_skill and best_idx == 0:
                best_idx = idx
        mixed.append(remaining.pop(best_idx))

    return mixed


def _cosine_similarity(query_vector: List[float], candidate_vector: Any) -> Optional[float]:
    """Return cosine similarity for stored embeddings; return None when unavailable."""
    if isinstance(candidate_vector, str):
        try:
            candidate_vector = json.loads(candidate_vector)
        except (TypeError, ValueError):
            return None
    if not isinstance(candidate_vector, (list, tuple)) or len(candidate_vector) != len(query_vector):
        return None
    try:
        dot = sum(float(a) * float(b) for a, b in zip(query_vector, candidate_vector))
        q_norm = sum(float(a) ** 2 for a in query_vector) ** 0.5
        c_norm = sum(float(b) ** 2 for b in candidate_vector) ** 0.5
        if not q_norm or not c_norm:
            return None
        return max(0.0, min(1.0, dot / (q_norm * c_norm)))
    except (TypeError, ValueError):
        return None


# Evidence hierarchy rank:
# diagnostic_assessment (highest) > quiz_verified (medium) > self_reported (baseline)
EVIDENCE_STRENGTH = {
    "diagnostic_assessment": 3,
    "quiz_verified": 2,
    "self_reported": 1,
}


# In-memory TTL caches for static occupational and curriculum catalogs
_career_cache: Dict[str, Dict[str, Any]] = {}
_career_skills_cache: Dict[str, Dict[str, Any]] = {}
_skills_lookup_cache: Dict[str, Dict[str, Any]] = {}
_skills_lookup_expiry: float = 0.0
CATALOG_CACHE_TTL = 3600.0  # 1 hour


class RecommendationService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.content_service = ContentService()
        self.history_service = LearningHistoryService()

    @staticmethod
    def get_cached_career(career_id: str) -> Dict[str, Any]:
        global _career_cache
        if career_id in _career_cache:
            return _career_cache[career_id]
        res = supabase_client.table("careers").select(
            "id, title, description, source_origin, review_status, onet_soc_code, esco_occupation_uri"
        ).eq("id", career_id).execute()
        career = res.data[0] if res.data else {}
        if career:
            _career_cache[career_id] = career
        return career

    @staticmethod
    def get_cached_career_skills(career_id: str) -> Dict[str, Dict[str, Any]]:
        global _career_skills_cache
        if career_id in _career_skills_cache:
            return _career_skills_cache[career_id]
        career_skills_map: Dict[str, Dict[str, Any]] = {}
        try:
            cs_res = supabase_client.table("career_skills").select(
                "skill_id, importance, importance_score, tier, rank, expected_proficiency, career_level, source_origin, review_status"
            ).eq("career_id", career_id).execute()
            for row in (cs_res.data or []):
                career_skills_map[row["skill_id"]] = row
            _career_skills_cache[career_id] = career_skills_map
        except Exception as e:
            logger.warning(f"Failed to fetch career_skills metadata for career {career_id}: {e}")
        return career_skills_map

    @staticmethod
    def get_cached_all_skills() -> Dict[str, Dict[str, Any]]:
        global _skills_lookup_cache, _skills_lookup_expiry
        import time as _t
        now = _t.time()
        if _skills_lookup_cache and now < _skills_lookup_expiry:
            return _skills_lookup_cache
        try:
            res = supabase_client.table("skills").select("id, name, category").execute()
            _skills_lookup_cache = {s["id"]: s for s in (res.data or [])}
            _skills_lookup_expiry = now + CATALOG_CACHE_TTL
        except Exception as e:
            logger.warning(f"Failed to fetch skills catalog: {e}")
        return _skills_lookup_cache

    async def get_recommendations_for_user(
        self,
        user_id: str,
        limit: int = 5,
        offset: int = 0,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes the Two-Stage Hybrid Recommendation Pipeline for a given user.
        """
        # 1. Fetch user's profile and target career
        profile_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
        if not profile_res.data or not profile_res.data[0].get("target_career_id"):
            logger.warning(f"User {user_id} has not selected a target career.")
            return []

        career_id = profile_res.data[0]["target_career_id"]
        career = self.get_cached_career(career_id)
        career_title = career.get("title", "General Career")

        # 2. Fetch user's enrolled skills and current proficiencies (Skill Graph Coordinates)
        user_skills_res = supabase_client.table("user_skills").select(
            "skill_id, proficiency, skills(id, name, category, onet_element_id, esco_skill_uri)"
        ).eq("user_id", user_id).execute()

        user_skills = []
        skill_proficiency_map: Dict[str, int] = {}
        skill_name_map: Dict[str, str] = {}

        for row in (user_skills_res.data or []):
            sk = row.get("skills")
            if sk:
                s_id = sk["id"]
                prof = int(row.get("proficiency", 20))
                user_skills.append({
                    "id": s_id,
                    "name": sk["name"],
                    "category": sk.get("category", ""),
                    "onet_element_id": sk.get("onet_element_id"),
                    "esco_skill_uri": sk.get("esco_skill_uri"),
                    "proficiency": prof,
                })
                skill_proficiency_map[s_id] = prof
                skill_name_map[s_id] = sk["name"]

        # If user has no skills mapped yet, return empty
        if not user_skills:
            logger.info(f"User {user_id} has no skills tracked in user_skills.")
            return []

        # 2B. Fetch Career Graph Metadata (Importance, Tiers, and Ranks)
        career_skills_map = self.get_cached_career_skills(career_id)

        # 2C. Fetch Skill Graph Dependencies (Prerequisites & DAG Relationships)
        user_skill_ids = set(s["id"] for s in user_skills)
        prerequisites_map: Dict[str, List[str]] = {}  # skill_id -> list of prerequisite_ids
        unblocks_map: Dict[str, List[str]] = {}        # prerequisite_id -> list of dependent skill_ids
        try:
            deps_as_target = supabase_client.table("skill_dependencies").select(
                "skill_id, prerequisite_id, relationship_type"
            ).in_("skill_id", list(user_skill_ids)).execute()
            for dep in (deps_as_target.data or []):
                if dep.get("relationship_type") == "requires":
                    prerequisites_map.setdefault(dep["skill_id"], []).append(dep["prerequisite_id"])

            deps_as_prereq = supabase_client.table("skill_dependencies").select(
                "skill_id, prerequisite_id, relationship_type"
            ).in_("prerequisite_id", list(user_skill_ids)).execute()
            for dep in (deps_as_prereq.data or []):
                if dep.get("relationship_type") == "requires":
                    unblocks_map.setdefault(dep["prerequisite_id"], []).append(dep["skill_id"])
        except Exception as e:
            logger.warning(f"Failed to fetch skill dependencies: {e}")

        # 3. Carry onboarding's O*NET/ESCO occupation, skill categories,
        # importance, proficiency targets, and evidence into semantic retrieval.
        def career_priority(skill):
            meta = career_skills_map.get(skill["id"], {})
            try:
                importance_score = float(meta.get("importance_score") or 0)
            except (TypeError, ValueError):
                importance_score = 0.0
            try:
                target = int(meta.get("expected_proficiency") or 100)
            except (TypeError, ValueError):
                target = 100
            gap_to_target = max(0, target - skill["proficiency"])
            essential = meta.get("importance") == "essential"
            tier = meta.get("tier") or 3
            rank = meta.get("rank") or 9999
            return (not essential, tier, -importance_score, -gap_to_target, rank, skill["proficiency"])

        priority_skills = sorted(user_skills, key=career_priority)[:4]
        career_tags = [
            f"{s['name']} [category: {s['category'] or 'General'}; "
            f"career importance: {career_skills_map.get(s['id'], {}).get('importance') or 'unclassified'}; "
            f"tier: {career_skills_map.get(s['id'], {}).get('tier') or 'unspecified'}; "
            f"importance score: {career_skills_map.get(s['id'], {}).get('importance_score') or 'unspecified'}; "
            f"learner estimate: {s['proficiency']}%; "
            f"target: {career_skills_map.get(s['id'], {}).get('expected_proficiency') or 'unspecified'}%]"
            for s in priority_skills
        ]
        frontier_query_text = (
            f"Target occupation: {career_title}. {career.get('description') or ''}. "
            f"Occupation provenance: {career.get('source_origin') or 'unspecified'}; "
            f"O*NET code: {career.get('onet_soc_code') or 'unspecified'}; "
            f"ESCO URI: {career.get('esco_occupation_uri') or 'unspecified'}. "
            f"Career skill priorities: {'; '.join(career_tags)}."
        )

        query_embedding = await self.embedding_service.get_embedding(frontier_query_text)

        # 4. STAGE 1: DATABASE COARSE FILTER (pgvector Semantic Recall)
        candidates: List[Dict[str, Any]] = []
        try:
            rpc_res = supabase_client.rpc(
                "match_micro_content",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.25,
                    "match_count": 100,
                }
            ).execute()
            if rpc_res.data:
                candidates = rpc_res.data
                logger.info(f"Stage 1 Coarse Filter retrieved {len(candidates)} candidates via match_micro_content RPC.")
        except Exception as e:
            logger.warning(f"match_micro_content RPC call failed ({e}); falling back to relational fetch.")

        # Filter explicit cross-career records before deciding whether recall is sufficient.
        candidates = _filter_candidates_for_career(candidates, career_title)

        # If the global semantic top set is too small after career/source filtering,
        # supplement it with a wider pool tied to the learner's enrolled skills.
        if len(candidates) < limit and user_skill_ids:
            try:
                table_res = supabase_client.table("micro_content").select("*").in_(
                    "associated_skill_id", list(user_skill_ids)
                ).limit(200).execute()
                seen_ids = {item.get("id") for item in candidates if item.get("id")}
                for item in (table_res.data or []):
                    if item.get("id") in seen_ids or not _lesson_matches_career(item, career_title):
                        continue
                    if item.get("similarity") is None:
                        item["similarity"] = _cosine_similarity(query_embedding, item.get("embedding"))
                    if item.get("similarity") is not None and item["similarity"] >= 0.25:
                        candidates.append(item)
                        if item.get("id"):
                            seen_ids.add(item["id"])
                candidates = _filter_candidates_for_career(candidates, career_title)
                logger.info(f"Career-filtered candidate pool contains {len(candidates)} lessons.")
            except Exception as e:
                logger.error(f"Failed to supplement targeted career candidate pool: {e}")

        # 4B. JUST-IN-TIME DYNAMIC CURRICULUM POPULATION
        # Verify how many candidate lessons actually match the learner's enrolled career skills
        relevant_candidates = [
            c for c in candidates
            if c.get("associated_skill_id") in user_skill_ids
        ]

        content_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for candidate in relevant_candidates:
            content_by_skill.setdefault(candidate.get("associated_skill_id"), []).append(candidate)

        def needs_source_diversity(skill):
            existing = content_by_skill.get(skill["id"], [])
            if not existing:
                return True
            urls = [item.get("source_url") for item in existing if item.get("source_url")]
            if not urls:
                return False  # Unknown source metadata is not evidence of low diversity.
            domains = {url.split("//", 1)[-1].split("/", 1)[0].lower() for url in urls}
            # Continue on-demand retrieval while a skill's known content comes from
            # only one source domain; exact URLs are excluded before fetching again.
            return len(domains) < 2

        skills_needing_content = [s for s in priority_skills if needs_source_diversity(s)]
        if not skills_needing_content:
            skills_needing_content = [s for s in user_skills if needs_source_diversity(s)]

        # Refill a short feed only when existing candidates are insufficient (< 4).
        # Never block a user with live dynamic generation when sufficient lessons already exist.
        excluded_ids = set(exclude_ids or [])
        remaining_relevant = sum(1 for item in relevant_candidates if item.get("id") not in excluded_ids)
        needs_refill = remaining_relevant < min(limit, 4)
        if needs_refill and not skills_needing_content:
            skills_needing_content = sorted(
                user_skills,
                key=lambda skill: len(content_by_skill.get(skill["id"], [])),
            )
        if needs_refill and skills_needing_content:
            needed_count = 1
            logger.info(
                f"Learner {user_id} ({career_title}) has {len(relevant_candidates)}/{limit} relevant lessons; "
                f"trying up to {needed_count} career-aware lessons from additional sources."
            )
            if skills_needing_content:
                sem = asyncio.Semaphore(2)

                async def _paced_gen(s):
                    async with sem:
                        try:
                            res = await asyncio.wait_for(
                                self.content_service.generate_dynamic_lesson_for_skill(
                                    skill_id=s["id"],
                                    skill_name=s["name"],
                                    category=s.get("category", "Core"),
                                    career_title=career_title,
                                    target_proficiency=s["proficiency"],
                                    career_skill_context=career_skills_map.get(s["id"], {}),
                                ),
                                timeout=7.0,
                            )
                            await asyncio.sleep(0.1)
                            return res
                        except asyncio.TimeoutError:
                            logger.warning(f"JIT generation timed out after 7.0s for '{s.get('name')}'; serving existing candidates.")
                            return None
                        except Exception as e:
                            logger.error(f"JIT generation error for '{s.get('name')}': {e}")
                            return None

                skills_to_generate = skills_needing_content[:needed_count] if skills_needing_content else [
                    s for s in priority_skills if needs_source_diversity(s)
                ][:needed_count]
                tasks = [_paced_gen(s) for s in skills_to_generate]
                try:
                    new_lessons = await asyncio.gather(*tasks, return_exceptions=True)
                    for lesson in new_lessons:
                        if isinstance(lesson, dict) and lesson.get("id"):
                            lesson["similarity"] = _cosine_similarity(query_embedding, lesson.get("embedding"))
                            if lesson["similarity"] is not None and lesson["similarity"] >= 0.25:
                                candidates.insert(0, lesson)
                                logger.info(f"Just-In-Time delivered tailored lesson: '{lesson.get('title')}'")
                except Exception as e:
                    logger.error(f"Error during Just-In-Time dynamic lesson generation: {e}")

        candidates = _filter_candidates_for_career(candidates, career_title)
        if not candidates:
            return []

        # Build skill details lookup for all skills in DB
        all_skills_map = self.get_cached_all_skills()

        # 5. STAGE 2: PYTHON GRAPH & PEDAGOGICAL RE-RANKER
        # Fetch user content activity history (impressions, opens, completions)
        user_activity_map = self.history_service.get_user_activity_map(user_id)

        ranked_items = []
        for item in candidates:
            # Missing semantic evidence must not be replaced with an invented baseline.
            try:
                base_sim = float(item.get("similarity", 0.0) or 0.0)
            except (TypeError, ValueError):
                base_sim = 0.0
            base_sim = max(0.0, min(1.0, base_sim))

            assoc_skill_id = item.get("associated_skill_id")
            user_prof = skill_proficiency_map.get(assoc_skill_id, 20)

            # A. Cognitive Load Gating (Difficulty Matching)
            # Target difficulty tiers: 20% -> Diff 1-2 | 50% -> Diff 2-3 | 80% -> Diff 3-4 | 100% -> Diff 4-5
            item_diff = int(item.get("difficulty_level") or 2)
            expected_diff = max(1, min(5, round(user_prof / 22.0) + 1))

            if item_diff > (expected_diff + 1):
                # Harsh penalty for prematurely exposing learner to advanced content
                diff_multiplier = max(0.40, 1.0 - 0.25 * (item_diff - expected_diff))
            elif item_diff <= expected_diff:
                # Accessible difficulty reward
                diff_multiplier = 1.08
            else:
                diff_multiplier = 1.00

            # B. Skill Gap & Mastery Prioritization
            # Unmastered skills get boosted proportionally to their deficit (gap_ratio).
            # Mastered skills (100% proficiency) are deprioritized relative to gap skills,
            # but remain eligible (0.65) for advanced extension or revision.
            if user_prof >= 100:
                gap_multiplier = 0.65
            elif user_prof >= 80:
                gap_multiplier = 0.85
            else:
                gap_ratio = (100 - user_prof) / 100.0
                gap_multiplier = 1.0 + (0.35 * gap_ratio)

            # C. Prerequisite Graph Signal (Skill Dependencies)
            # Rule: If Skill B requires Prerequisite A, weak proficiency in A penalizes B (not A!).
            # Missing data != verified zero: distinguish unknown skill from verified low proficiency (< 60%).
            req_prereqs = prerequisites_map.get(assoc_skill_id, [])
            has_unmet_prereq = False
            prereq_penalty = 1.0

            if req_prereqs:
                for p_id in req_prereqs:
                    if p_id in skill_proficiency_map:
                        p_prof = skill_proficiency_map[p_id]
                        if p_prof < 60:
                            # Confirmed weak proficiency in prerequisite: apply ranking penalty
                            has_unmet_prereq = True
                            prereq_penalty = min(prereq_penalty, 0.50)
                    else:
                        # Missing skill record in profile: learner was unassessed on this prerequisite.
                        # Apply a mild uncertainty discount (0.85) rather than a severe penalty.
                        prereq_penalty = min(prereq_penalty, 0.85)

            # Foundational Unblocking Boost:
            # If this skill is a prerequisite that unblocks OTHER career skills, and the learner hasn't mastered it (< 60%),
            # prioritizing this foundational skill unlocks the downstream career path.
            is_foundational_unblocker = (assoc_skill_id in unblocks_map) and (user_prof < 60)
            unblocking_boost = 1.15 if is_foundational_unblocker else 1.00

            # D. Career Graph Metadata (O*NET/ESCO Importance, Tiers, and Ranks)
            # Priority for essential career competencies and foundational tiers.
            cs_meta = career_skills_map.get(assoc_skill_id, {})
            importance = (cs_meta.get("importance") or "").lower()
            tier = cs_meta.get("tier")
            importance_score = cs_meta.get("importance_score")
            try:
                importance_score_val = float(importance_score) if importance_score is not None else None
            except (ValueError, TypeError):
                importance_score_val = None

            if importance == "essential" or tier == 1 or (importance_score_val and importance_score_val >= 0.75):
                career_importance_multiplier = 1.15  # Essential / Tier 1 career competency
            elif importance == "differentiator" or tier == 2 or (importance_score_val and importance_score_val >= 0.50):
                career_importance_multiplier = 1.05  # Core supporting skill
            else:
                career_importance_multiplier = 1.00  # Optional / baseline skill

            # E. Keep source metadata for compatibility; uncalibrated source labels
            # must not act as a numeric quality score in the ranking.
            trust_score = item.get("source_trust_score")
            source_quality_multiplier = _source_quality_multiplier(item, career_title)

            # G. Learning History & Content Activity Adaptation
            content_act = user_activity_map.get(item["id"], {})
            times_rec = content_act.get("times_recommended", 0)
            opened = bool(content_act.get("opened_at"))
            completed = bool(content_act.get("completed_at"))
            has_passed_this_lesson = self.history_service.has_passed_lesson(user_id, item["id"])
            last_seen_str = content_act.get("last_seen_at")

            # Check if impression was delivered during the active browsing session (< 5 minutes ago)
            is_recent_session_impression = False
            if last_seen_str:
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                    age_seconds = (datetime.now(timezone.utc) - last_seen_dt).total_seconds()
                    if age_seconds < 300:
                        is_recent_session_impression = True
                except Exception:
                    pass

            if has_passed_this_lesson:
                # Completed and passed: heavily suppress from standard feed to prevent repetition
                activity_multiplier = 0.20
                lifecycle_state = "completed_passed"
            elif completed and not has_passed_this_lesson:
                # Completed reading / attempted quiz but failed: surface for retry or alternate source
                activity_multiplier = 0.70
                lifecycle_state = "retry_needed"
            elif opened and not has_passed_this_lesson:
                # Opened/read in-app or external source, quiz not yet completed: boost so learner finishes!
                activity_multiplier = 1.12
                lifecycle_state = "in_progress_opened"
            elif times_rec >= 1 and not opened and not is_recent_session_impression:
                # Each prior impression lowers the chance of resurfacing an ignored lesson.
                activity_multiplier = max(0.45, 0.82 ** min(int(times_rec), 4))
                lifecycle_state = "ignored" if times_rec >= 3 else "fresh"
            elif times_rec >= 2:
                activity_multiplier = max(0.68, 0.90 ** min(int(times_rec) - 1, 3))
                lifecycle_state = "fresh"
            else:
                activity_multiplier = 1.00
                lifecycle_state = "fresh"

            # Composite Re-Rank Score:
            final_score = (
                base_sim
                * diff_multiplier
                * gap_multiplier
                * prereq_penalty
                * unblocking_boost
                * career_importance_multiplier
                * source_quality_multiplier
                * activity_multiplier
            )

            # Enrich item for frontend presentation
            skill_info = all_skills_map.get(assoc_skill_id, {})
            skill_name = skill_info.get("name") or "Core Skill"
            skill_category = skill_info.get("category") or "Technical"

            # Parse quizzes, summary bullets, and self-contained lesson fields safely
            quizzes_data = item.get("quizzes")
            summary_bullets = item.get("summary_bullets") or item.get("summary") or ""
            concept_overview = item.get("concept_overview") or ""
            practice_scenario = item.get("practice_scenario") or ""
            source_name = item.get("source_name") or item.get("source") or ""
            video_id = item.get("video_id")

            if item.get("content"):
                try:
                    c_data = item.get("content")
                    if isinstance(c_data, str):
                        c_data = json.loads(c_data)
                    if isinstance(c_data, dict):
                        if not quizzes_data:
                            quizzes_data = c_data.get("quizzes")
                        if not summary_bullets:
                            summary_bullets = c_data.get("summary_bullets") or c_data.get("summary") or ""
                        if not concept_overview:
                            concept_overview = c_data.get("concept_overview") or ""
                        if not practice_scenario:
                            practice_scenario = c_data.get("practice_scenario") or ""
                        if not source_name:
                            source_name = c_data.get("source_name") or c_data.get("source") or ""
                        if not video_id:
                            video_id = c_data.get("video_id")
                except Exception:
                    pass

            if isinstance(quizzes_data, str):
                try:
                    quizzes_data = json.loads(quizzes_data)
                except Exception:
                    quizzes_data = []

            from app.services.content_service import classify_source_adapter
            source_url_str = item.get("source_url", "")
            source_adapter = classify_source_adapter(source_url_str, source_name)
            if not source_name:
                adapter_labels = {
                    "youtube": "YouTube Lecture",
                    "structured_tutorial": "Structured Tutorial",
                    "open_textbook": "Open Textbook",
                    "clinical_science": "NCBI / Europe PMC",
                    "mdn": "MDN Web Docs",
                    "openalex": "OpenAlex Academic",
                    "wikipedia": "Wikipedia Reference",
                }
                source_name = adapter_labels.get(source_adapter, "Instructional Guide")

            ranked_items.append({
                "id": item["id"],
                "title": item["title"],
                "source_url": source_url_str,
                "source_name": source_name,
                "source_adapter": source_adapter,
                "video_id": video_id,
                "summary_bullets": summary_bullets,
                "concept_overview": concept_overview,
                "practice_scenario": practice_scenario,
                "difficulty_level": item_diff,
                "source_trust_score": trust_score,
                "source_quality_multiplier": source_quality_multiplier,
                "quizzes": quizzes_data or [],
                "associated_skill_id": assoc_skill_id,
                "skill_id": assoc_skill_id,
                "skill_name": skill_name,
                "skill_category": skill_category,
                "user_current_proficiency": user_prof,
                "has_unmet_prerequisites": has_unmet_prereq,
                "is_unblocking": is_foundational_unblocker,
                "career_importance": importance or "standard",
                "career_tier": tier,
                "times_recommended": times_rec,
                "opened": opened,
                "completed": completed,
                "has_passed": has_passed_this_lesson,
                "lifecycle_state": lifecycle_state,
                "relevance_score": round(final_score, 4),
            })

        # Sort descending by composite re-ranked score
        ranked_items.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Diversity adjustment: prevent feed monopoly where all items belong to a single skill
        seen_skill_counts: Dict[str, int] = {}
        for it in ranked_items:
            s_id = it.get("associated_skill_id")
            count = seen_skill_counts.get(s_id, 0)
            if count > 0:
                it["relevance_score"] = round(it["relevance_score"] * (0.85 ** count), 4)
            seen_skill_counts[s_id] = count + 1

        # Re-sort after diversity balancing
        ranked_items.sort(key=lambda x: x["relevance_score"], reverse=True)

        available_items = [item for item in ranked_items if item["id"] not in excluded_ids]
        slice_pool = available_items[offset:]
        final_feed = _apply_feed_mixer(slice_pool, limit)

        # Record feed impressions for delivered items
        delivered_ids = [it["id"] for it in final_feed]
        self.history_service.record_impressions(user_id, delivered_ids)

        return final_feed

    async def get_completed_library_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns all micro-learning lessons that the learner has passed (`passed == True`),
        formatted for the Completed & Reviewed Library tab.
        """
        passed_lesson_ids: List[str] = []
        try:
            from app.services.learning_history_service import ATTEMPTS_FILE
            if os.path.exists(ATTEMPTS_FILE):
                with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
                    all_attempts = json.load(f)
                for a in all_attempts:
                    if a.get("user_id") == user_id and a.get("passed") is True and a.get("lesson_id"):
                        if a["lesson_id"] not in passed_lesson_ids:
                            passed_lesson_ids.append(a["lesson_id"])
        except Exception:
            pass

        if not passed_lesson_ids:
            return []

        try:
            res = supabase_client.table("micro_content").select("*").in_("id", passed_lesson_ids).execute()
            rows = res.data or []
            skill_ids = list({r.get("associated_skill_id") for r in rows if r.get("associated_skill_id")})
            skill_map = {}
            if skill_ids:
                sk_res = supabase_client.table("skills").select("id, name, category").in_("id", skill_ids).execute()
                skill_map = {s["id"]: s for s in (sk_res.data or [])}

            from app.services.content_service import classify_source_adapter
            adapter_labels = {
                "youtube": "YouTube Lecture",
                "structured_tutorial": "Structured Tutorial",
                "open_textbook": "Open Textbook",
                "clinical_science": "NCBI / Europe PMC",
                "mdn": "MDN Web Docs",
                "openalex": "OpenAlex Academic",
                "wikipedia": "Wikipedia Reference",
            }
            library = []
            for item in rows:
                sid = item.get("associated_skill_id")
                sk = skill_map.get(sid, {})
                source_url = item.get("source_url", "")
                c_raw = item.get("content")
                c_data = {}
                if isinstance(c_raw, dict):
                    c_data = c_raw
                elif isinstance(c_raw, str) and c_raw.strip().startswith("{"):
                    try:
                        c_data = json.loads(c_raw)
                    except Exception:
                        c_data = {}
                quizzes = item.get("quizzes") or c_data.get("quizzes") or []
                if isinstance(quizzes, str):
                    try:
                        quizzes = json.loads(quizzes)
                    except Exception:
                        quizzes = []
                source_name = item.get("source_name") or c_data.get("source_name") or ""
                source_adapter = classify_source_adapter(source_url, source_name)
                if not source_name:
                    source_name = adapter_labels.get(source_adapter, "Instructional Guide")
                library.append({
                    "id": item["id"],
                    "title": item.get("title", "Lesson"),
                    "summary_bullets": item.get("summary_bullets") or item.get("summary") or c_data.get("summary_bullets") or "",
                    "concept_overview": item.get("concept_overview") or c_data.get("concept_overview") or "",
                    "practice_scenario": item.get("practice_scenario") or c_data.get("practice_scenario") or "",
                    "video_id": item.get("video_id") or c_data.get("video_id"),
                    "source_url": source_url,
                    "source_name": source_name,
                    "source_adapter": source_adapter,
                    "quizzes": quizzes,
                    "associated_skill_id": sid,
                    "skill_id": sid,
                    "skill_name": sk.get("name", "Core Skill"),
                    "skill_category": sk.get("category", "General"),
                    "has_passed": True,
                    "completed": True,
                    "lifecycle_state": "passed_complete",
                    "learning_status": "completed",
                })
            return library
        except Exception as e:
            logger.warning(f"Failed to load completed library for {user_id}: {e}")
            return []

    async def submit_quiz_answer(
        self,
        user_id: str,
        lesson_id: str,
        answers: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        Evaluates a submitted quiz server-side, provides instant feedback,
        prevents repeated-pass farming, preserves evidence hierarchy,
        records attempt history, and safely updates user_skills proficiency.
        """
        # 1. Fetch lesson details server-side
        lesson_res = supabase_client.table("micro_content").select("*").eq("id", lesson_id).execute()
        if not lesson_res.data:
            return {"error": "Lesson not found"}

        lesson = lesson_res.data[0]
        quizzes = lesson.get("quizzes", [])
        if isinstance(quizzes, str):
            try:
                quizzes = json.loads(quizzes)
            except Exception:
                quizzes = []

        total_questions = len(quizzes)
        if total_questions == 0:
            return {"error": "This lesson does not have an active quiz."}

        # 2. Evaluate each question strictly against stored server answer key
        correct_count = 0
        detailed_feedback = []

        for idx, q in enumerate(quizzes):
            expected_answer = q.get("answer", "").strip()
            user_choice = answers.get(idx) or answers.get(str(idx)) or ""
            user_choice = str(user_choice).strip()

            is_correct = (user_choice == expected_answer)
            if is_correct:
                correct_count += 1

            detailed_feedback.append({
                "question_index": idx,
                "question": q.get("question", ""),
                "user_answer": user_choice,
                "correct_answer": expected_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

        percentage = round((correct_count / total_questions) * 100, 1)
        passed = (percentage >= 60.0)

        # 3. Check for repeated-pass farming via learning history service
        already_passed = self.history_service.has_passed_lesson(user_id, lesson_id)

        # Durably record this attempt with attempt_number in assessment history
        skill_id = lesson.get("associated_skill_id")
        self.history_service.record_attempt(
            user_id=user_id,
            lesson_id=lesson_id,
            skill_id=skill_id,
            answers=answers,
            score=correct_count,
            total=total_questions,
            percentage=percentage,
            passed=passed,
        )

        # Mark completion in user_content_activity
        self.history_service.record_content_completion(user_id, lesson_id)

        # 4. Bounded Proficiency Progression
        new_proficiency = None
        skill_mastered = False
        proficiency_increment = 0

        if skill_id:
            user_skill_res = supabase_client.table("user_skills").select("*").eq(
                "user_id", user_id
            ).eq("skill_id", skill_id).execute()

            if user_skill_res.data:
                current_row = user_skill_res.data[0]
                current_prof = int(current_row.get("proficiency", 20))
                current_evidence = current_row.get("evidence_source", "self_reported")

                # Difficulty Ceiling rule: Beginner (Level 1) lessons cannot certify Expert (100%) mastery
                raw_diff = lesson.get("difficulty_level")
                ceiling_map = {1: 50, 2: 70, 3: 85, 4: 95, 5: 100}
                diff_ceiling = ceiling_map.get(int(raw_diff), 100) if raw_diff is not None else 100

                if passed and not already_passed:
                    if current_prof >= diff_ceiling:
                        # Already above this difficulty tier's ceiling: award +2% review credit
                        proficiency_increment = min(2, 100 - current_prof)
                    elif raw_diff is not None and int(raw_diff) >= 3 and percentage == 100.0:
                        # Perfect score bonus on Intermediate/Advanced/Expert lesson
                        proficiency_increment = 12
                    else:
                        proficiency_increment = 10
                    new_proficiency = min(100, current_prof + proficiency_increment)
                else:
                    # Repeated pass or failed attempt earns 0 increment
                    proficiency_increment = 0
                    new_proficiency = current_prof

                skill_mastered = (new_proficiency >= 100)

                update_payload = {"proficiency": new_proficiency}

                # Preserve evidence hierarchy: NEVER downgrade diagnostic_assessment to quiz_verified
                if passed:
                    if EVIDENCE_STRENGTH.get(current_evidence, 0) < EVIDENCE_STRENGTH["quiz_verified"]:
                        update_payload["evidence_source"] = "quiz_verified"

                supabase_client.table("user_skills").update(update_payload).eq(
                    "user_id", user_id
                ).eq("skill_id", skill_id).execute()

            else:
                # Skill is not yet enrolled in user's profile: initialize record
                if passed and not already_passed:
                    proficiency_increment = 10
                    new_proficiency = 30  # Baseline 20 + 10 quiz verified
                else:
                    proficiency_increment = 0
                    new_proficiency = 20

                skill_mastered = False
                new_evidence = "quiz_verified" if passed else "self_reported"

                supabase_client.table("user_skills").insert({
                    "user_id": user_id,
                    "skill_id": skill_id,
                    "proficiency": new_proficiency,
                    "evidence_source": new_evidence,
                }).execute()

        # Repeated failure guidance ("Ask MENTOR" trigger)
        ask_mentor_suggested = not passed

        return {
            "passed": passed,
            "score": correct_count,
            "total": total_questions,
            "percentage": percentage,
            "proficiency_increment": proficiency_increment,
            "new_proficiency": new_proficiency,
            "skill_mastered": skill_mastered,
            "already_completed": already_passed,
            "ask_mentor_suggested": ask_mentor_suggested,
            "learning_status": "completed" if passed else "retry_needed",
            "feedback": detailed_feedback,
        }
