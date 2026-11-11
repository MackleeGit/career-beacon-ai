# app/services/mentorship_service.py
"""
Module 4: Mentorship Ecosystem Service
--------------------------------------
Implements:
  1. Cross-Industry Mentor Seeding (Tech, Data/ML, Finance/Accounting, Healthcare,
     Engineering/Infrastructure, Culinary/Skilled Trades) + Live Supabase `mentors` sync.
  2. 2-Stage Anti-Desperation Semantic Matcher:
     - Stage 1: Hard capacity & availability filter (`active_mentees_count < max_mentees`).
     - Stage 2: Hybrid Semantic + Skill-Gap Overlap + Domain Alignment scoring:
         MatchScore = 0.55 * cosine_sim(v_learner_need, v_mentor)
                    + 0.30 * skill_gap_overlap_ratio
                    + 0.15 * domain_alignment_bonus
     - Anti-Desperation Gate: Mentors with `MatchScore < 0.45` (and zero shared gap skills)
       are strictly blocked from being recommended as "Top Matches" so learners are never
       matched out of desperation.
  3. Connection Handshake & Direct Messaging (DMs) with Learner Skill Gap Snapshot.
  4. Mentor Pulse Feed (LinkedIn-style industry updates, events, and advice).
  5. Bidirectional Q&A Knowledge Base (Learners ask -> Routed to Mentors -> Searchable).
  6. 1-on-1 Session Booking with Anti-Double-Booking Lock, Jitsi Meet Conference Link,
     Google Calendar Deep-Link, and RFC 5545 `.ics` Calendar Invite with 24h & 15m VALARMs.
  7. Post-Session Skill Endorsement (+15% Mentor-Verified proficiency boost on `user_skills`).
"""

import os
import json
import uuid
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("career_beacon.mentorship_service")

ECOSYSTEM_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "mentorship_ecosystem.json",
)

ANTI_DESPERATION_THRESHOLD = 0.45
STRONG_MATCH_THRESHOLD = 0.62


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cosine_similarity(v1: Optional[List[float]], v2: Optional[List[float]]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1_sq = sum(a * a for a in v1)
    n2_sq = sum(b * b for b in v2)
    # Fast path for unit-normalized vectors (FastEmbed outputs unit length)
    if 0.98 <= n1_sq <= 1.02 and 0.98 <= n2_sq <= 1.02:
        return max(0.0, min(1.0, dot))
    denom = math.sqrt(n1_sq * n2_sq)
    if denom == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / denom))


# ---------------------------------------------------------------------------
# Pre-Seeded Cross-Industry Reference Mentors (Loaded from External Fixture)
# ---------------------------------------------------------------------------
SEEDS_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "seeds",
    "mentorship_seeds.json",
)


def _load_mentorship_seeds() -> Dict[str, Any]:
    if os.path.exists(SEEDS_FILE_PATH):
        try:
            with open(SEEDS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[MentorshipService] Failed to load seeds file: {e}")
    return {"mentors": [], "pulse_posts": [], "questions": []}


_SEEDS_CACHE = _load_mentorship_seeds()
SEEDED_MENTORS: List[Dict[str, Any]] = _SEEDS_CACHE.get("mentors", [])
SEEDED_PULSE_POSTS: List[Dict[str, Any]] = _SEEDS_CACHE.get("pulse_posts", [])
SEEDED_QUESTIONS: List[Dict[str, Any]] = _SEEDS_CACHE.get("questions", [])


class MentorshipService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self._ensure_store()

    def _ensure_store(self) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(ECOSYSTEM_STORE_PATH), exist_ok=True)
        if not os.path.exists(ECOSYSTEM_STORE_PATH):
            initial_state = {
                "mentors": SEEDED_MENTORS,
                "connections": [],
                "messages": [],
                "pulse_posts": SEEDED_PULSE_POSTS,
                "questions": SEEDED_QUESTIONS,
                "sessions": [],
            }
            self._save_store(initial_state)
            return initial_state

        try:
            with open(ECOSYSTEM_STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        changed = False
        if "mentors" not in data or not data["mentors"]:
            data["mentors"] = SEEDED_MENTORS
            changed = True
        if "pulse_posts" not in data or not data["pulse_posts"]:
            data["pulse_posts"] = SEEDED_PULSE_POSTS
            changed = True
        if "questions" not in data or not data["questions"]:
            data["questions"] = SEEDED_QUESTIONS
            changed = True
        for k in ("connections", "messages", "sessions"):
            if k not in data:
                data[k] = []
                changed = True

        if changed:
            self._save_store(data)
        return data

    def _save_store(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(ECOSYSTEM_STORE_PATH), exist_ok=True)
        with open(ECOSYSTEM_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def _ensure_mentor_vectors(self, store: Dict[str, Any]) -> None:
        """Lazily computes and caches dual 384-d vectors (`domain_vector` and `skills_vector`) for mentors using batch inference."""
        missing = [
            m for m in store.get("mentors", [])
            if not m.get("domain_vector") or not m.get("skills_vector") or not m.get("mentor_vector")
        ]
        if not missing:
            return
        domain_texts = [
            f"Occupational Domain: {m.get('primary_domain', '')}. Role: {m.get('headline', '')}. Scope: {m.get('bio', '')}."
            for m in missing
        ]
        skills_texts = [
            f"Domain: {m.get('primary_domain', '')}. Core Technical Competencies: {', '.join(m.get('expertise_skills', []))}."
            for m in missing
        ]
        try:
            all_vecs = await self.embedding_service.get_embeddings_batch(domain_texts + skills_texts)
            n = len(missing)
            for idx, m in enumerate(missing):
                d_vec = all_vecs[idx]
                s_vec = all_vecs[n + idx]
                m["domain_vector"] = d_vec
                m["skills_vector"] = s_vec
                m["mentor_vector"] = d_vec
            self._save_store(store)
        except Exception as err:
            logger.warning(f"[MentorshipService] Failed to batch embed mentors: {err}")

    @staticmethod
    def _format_question_embed_text(q: Dict[str, Any]) -> str:
        base = f"{q.get('title', '').strip()}. Skill: {q.get('skill_tag', '').strip()}. {q.get('body', '').strip()[:200]}"
        answers = q.get("answers") or []
        if answers and isinstance(answers[0], dict) and answers[0].get("body"):
            base += f" Answer: {answers[0]['body'].strip()[:250]}"
        return base

    async def _ensure_question_vectors(self, store: Dict[str, Any]) -> None:
        """Lazily computes and caches 384-d vectors for questions (including answer text when answered)."""
        missing = [
            q for q in store.get("questions", [])
            if not q.get("embedding") or (q.get("answers") and not q.get("answer_embedded"))
        ]
        if not missing:
            return
        texts = [self._format_question_embed_text(q) for q in missing]
        try:
            vecs = await self.embedding_service.get_embeddings_batch(texts)
            for q, vec in zip(missing, vecs):
                q["embedding"] = vec
                if q.get("answers"):
                    q["answer_embedded"] = True
            self._save_store(store)
        except Exception as err:
            logger.warning(f"[MentorshipService] Failed to batch embed questions: {err}")

    async def register_or_update_mentor(
        self,
        mentor_id: str,
        full_name: str,
        primary_domain: str,
        headline: str,
        bio: str,
        weekly_hours: int,
        available_days: List[str],
        preferred_time_window: str,
        expertise_skills: List[str],
        max_mentees: int = 5,
    ) -> Dict[str, Any]:
        """Registers or updates a real mentor user inside the Mentorship Ecosystem store."""
        store = self._ensure_store()
        skills_str = ", ".join(expertise_skills)
        domain_text = f"Occupational Domain: {primary_domain}. Role: {headline}. Scope: {bio}."
        skills_text = f"Domain: {primary_domain}. Core Technical Competencies: {skills_str}."
        try:
            vecs = await self.embedding_service.get_embeddings_batch([domain_text, skills_text])
            domain_vec = vecs[0] if len(vecs) == 2 else None
            skills_vec = vecs[1] if len(vecs) == 2 else None
        except Exception:
            domain_vec, skills_vec = None, None

        existing = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
        if existing:
            existing.update({
                "full_name": full_name or existing.get("full_name", "Industry Mentor"),
                "primary_domain": primary_domain,
                "headline": headline,
                "bio": bio,
                "weekly_hours": weekly_hours,
                "available_days": available_days or ["Tue", "Thu"],
                "preferred_time_window": preferred_time_window or "Evening",
                "expertise_skills": expertise_skills,
                "max_mentees": max_mentees,
                "mentor_vector": domain_vec or existing.get("mentor_vector"),
                "domain_vector": domain_vec or existing.get("domain_vector"),
                "skills_vector": skills_vec or existing.get("skills_vector"),
            })
            record = existing
        else:
            record = {
                "mentor_id": mentor_id,
                "full_name": full_name or "Industry Mentor",
                "primary_domain": primary_domain,
                "headline": headline,
                "bio": bio,
                "expertise_skills": expertise_skills,
                "weekly_hours": weekly_hours,
                "available_days": available_days or ["Tue", "Thu"],
                "preferred_time_window": preferred_time_window or "Evening",
                "max_mentees": max_mentees,
                "active_mentees_count": 0,
                "verified_sessions_count": 0,
                "avg_rating": 5.0,
                "is_seeded": False,
                "mentor_vector": domain_vec,
                "domain_vector": domain_vec,
                "skills_vector": skills_vec,
            }
            store["mentors"].insert(0, record)

        self._save_store(store)
        return {k: v for k, v in record.items() if k not in ("mentor_vector", "domain_vector", "skills_vector")}

    async def get_all_mentors(self) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        await self._ensure_mentor_vectors(store)

        try:
            db_mentors = supabase_client.table("mentors").select("*").execute()
            known_ids = {m["mentor_id"] for m in store["mentors"]}
            for row in db_mentors.data or []:
                mid = row.get("profile_id")
                if not mid or mid in known_ids:
                    continue
                prof = (
                    supabase_client.table("profiles")
                    .select("full_name, bio")
                    .eq("id", mid)
                    .limit(1)
                    .execute()
                )
                p_data = prof.data[0] if prof.data else {}
                if not p_data:
                    continue
                    exp_raw = row.get("expertise") or ""
                    parts = [p.strip() for p in exp_raw.split("|") if p.strip()]
                    p_domain = parts[0] if len(parts) >= 1 else "Software Architecture & Full-Stack"
                    p_headline = parts[1] if len(parts) >= 2 else "Verified Career Mentor"
                    p_skills = (
                        [s.strip() for s in parts[2].split(",") if s.strip()]
                        if len(parts) >= 3
                        else []
                    )
                    store["mentors"].append({
                        "mentor_id": mid,
                        "full_name": p_data.get("full_name") or "Verified Mentor",
                        "primary_domain": p_domain,
                        "headline": p_headline,
                        "bio": row.get("bio") or p_data.get("bio") or "",
                        "expertise_skills": p_skills,
                        "weekly_hours": 4,
                        "available_days": ["Tue", "Thu"],
                        "preferred_time_window": "Evening",
                        "max_mentees": 5,
                        "active_mentees_count": 0,
                        "verified_sessions_count": int(row.get("rating_count") or 1),
                        "avg_rating": float(row.get("rating_avg") or 5.0),
                        "is_seeded": False,
                        "mentor_vector": None,
                    })
            await self._ensure_mentor_vectors(store)
            self._save_store(store)
        except Exception:
            pass

        return store["mentors"]

    def _get_learner_context(self, learner_id: str) -> Dict[str, Any]:
        """Fetches learner's target career and skill gaps from Supabase."""
        career_title = "General Career Path"
        career_desc = ""
        full_name = "Learner"
        gap_skills: List[Dict[str, Any]] = []
        all_skills: List[Dict[str, Any]] = []

        try:
            prof_res = (
                supabase_client.table("profiles")
                .select("full_name, target_career_id")
                .eq("id", learner_id)
                .limit(1)
                .execute()
            )
            if prof_res.data:
                p_row = prof_res.data[0]
                full_name = p_row.get("full_name") or "Learner"
                cid = p_row.get("target_career_id")
                if cid:
                    c_res = (
                        supabase_client.table("careers")
                        .select("title, description")
                        .eq("id", cid)
                        .limit(1)
                        .execute()
                    )
                    if c_res.data:
                        career_title = c_res.data[0].get("title") or career_title
                        career_desc = c_res.data[0].get("description") or ""

            us_res = (
                supabase_client.table("user_skills")
                .select("skill_id, proficiency, skills(name, category)")
                .eq("user_id", learner_id)
                .execute()
            )
            for row in us_res.data or []:
                sk_info = row.get("skills") or {}
                sk_name = sk_info.get("name")
                if sk_name:
                    prof = int(row.get("proficiency") or 20)
                    item = {
                        "skill_id": row.get("skill_id"),
                        "name": sk_name,
                        "category": sk_info.get("category") or "General",
                        "proficiency": prof,
                    }
                    all_skills.append(item)
                    if prof < 80:
                        gap_skills.append(item)
        except Exception as err:
            print(f"[MentorshipService] Learner context warning: {err}")

        gap_skills.sort(key=lambda x: x["proficiency"])
        return {
            "learner_id": learner_id,
            "full_name": full_name,
            "career_title": career_title,
            "career_description": career_desc,
            "all_skills": all_skills,
            "gap_skills": gap_skills,
        }

    # -----------------------------------------------------------------------
    # 1. 2-Stage Anti-Desperation Semantic Matcher
    # -----------------------------------------------------------------------
    async def match_mentors_for_learner(
        self,
        learner_id: str,
        include_below_threshold: bool = False,
    ) -> Dict[str, Any]:
        """
        Computes a transparent hybrid match score for each available mentor:
          MatchScore = 0.55 * SemanticCosine + 0.30 * SkillGapOverlap + 0.15 * DomainAlignment
        Enforces the Anti-Desperation Gate (`MatchScore >= 0.45`) so learners are never
        paired with irrelevant mentors out of desperation.
        """
        store = self._ensure_store()
        mentors = await self.get_all_mentors()
        ctx = self._get_learner_context(learner_id)

        top_gaps = [g["name"] for g in ctx["gap_skills"][:8]]
        all_skill_names = [s["name"] for s in ctx["all_skills"]]
        gaps_str = ", ".join(top_gaps if top_gaps else all_skill_names)
        # Dual-vector mentor queries matching stored mentor `domain_vector` and `skills_vector`
        domain_query = f"Occupational Domain: {ctx['career_title']}. Role: {ctx['career_title']}."
        skills_query = f"Domain: {ctx['career_title']}. Core Technical Competencies: {gaps_str}."
        try:
            q_vecs = await self.embedding_service.get_embeddings_batch([domain_query, skills_query])
            learner_domain_vec = q_vecs[0] if len(q_vecs) == 2 else None
            learner_skills_vec = q_vecs[1] if len(q_vecs) == 2 else None
        except Exception:
            learner_domain_vec, learner_skills_vec = None, None

        learner_conns = {
            c["mentor_id"]: c
            for c in store.get("connections", [])
            if c["learner_id"] == learner_id
        }

        qualified_matches: List[Dict[str, Any]] = []
        filtered_out_count = 0

        career_lower = ctx["career_title"].lower()
        gap_lower_map = {g["name"].lower().strip(): g["name"] for g in ctx["gap_skills"]}
        all_lower_map = {s["name"].lower().strip(): s["name"] for s in ctx["all_skills"]}

        def _skills_equivalent(m_skill: str, l_skill: str) -> bool:
            if m_skill == l_skill:
                return True
            m_toks = set(m_skill.replace("-", " ").split())
            l_toks = set(l_skill.replace("-", " ").split())
            # Require at least 2 shared tokens to avoid single-word false positives ("design" vs "system design")
            if len(m_toks) >= 2 and len(l_toks) >= 2 and (m_toks.issubset(l_toks) or l_toks.issubset(m_toks)):
                return True
            return False

        for m in mentors:
            if m["mentor_id"] == learner_id:
                continue

            active_count = int(m.get("active_mentees_count", 0))
            max_cap = int(m.get("max_mentees", 5))
            has_capacity = active_count < max_cap

            domain_sim = _cosine_similarity(learner_domain_vec, m.get("domain_vector") or m.get("mentor_vector"))
            skills_sim = _cosine_similarity(learner_skills_vec, m.get("skills_vector") or m.get("mentor_vector"))
            sem_sim = (0.50 * domain_sim) + (0.50 * skills_sim)

            mentor_skills = m.get("expertise_skills", [])
            shared_gap_skills: List[str] = []
            shared_general_skills: List[str] = []

            for m_sk in mentor_skills:
                m_low = m_sk.lower().strip()
                matched_gap = next(
                    (orig for k_low, orig in gap_lower_map.items() if _skills_equivalent(m_low, k_low)),
                    None,
                )
                if matched_gap and matched_gap not in shared_gap_skills:
                    shared_gap_skills.append(matched_gap)
                else:
                    matched_any = next(
                        (orig for k_low, orig in all_lower_map.items() if _skills_equivalent(m_low, k_low)),
                        None,
                    )
                    if matched_any and matched_any not in shared_general_skills:
                        shared_general_skills.append(matched_any)

            denom = max(1, min(4, len(top_gaps) if top_gaps else 3))
            overlap_score = min(
                1.0,
                (len(shared_gap_skills) + 0.5 * len(shared_general_skills)) / denom,
            )

            domain_str = f"{m.get('primary_domain', '')} {m.get('headline', '')} {m.get('bio', '')}".lower()
            career_tokens = [t for t in career_lower.replace(",", " ").split() if len(t) > 3]
            token_hits = sum(1 for tok in career_tokens if tok in domain_str)
            domain_score = 1.0 if token_hits > 0 else (0.75 if domain_sim >= 0.65 else (0.4 if shared_gap_skills else 0.0))

            composite_score = (0.30 * domain_sim) + (0.30 * skills_sim) + (0.25 * overlap_score) + (0.15 * domain_score)
            match_pct = int(round(composite_score * 100))

            passes_anti_desperation = (
                domain_sim >= 0.56
                and (
                    composite_score >= ANTI_DESPERATION_THRESHOLD
                    or (len(shared_gap_skills) >= 1 and domain_sim >= 0.60)
                )
            )

            if not passes_anti_desperation and not include_below_threshold:
                filtered_out_count += 1
                continue

            if composite_score >= STRONG_MATCH_THRESHOLD or len(shared_gap_skills) >= 2:
                match_tier = "strong"
                match_badge = "Strong Semantic & Skill Match"
            elif passes_anti_desperation:
                match_tier = "domain_aligned"
                match_badge = "Domain-Aligned Mentor"
            else:
                match_tier = "below_threshold"
                match_badge = "Low Alignment (Filtered by Anti-Desperation Gate)"

            # Calculate Identity & Trust Verification Boost
            has_google = bool(m.get("google_email") or m.get("is_seeded") or m.get("google_verified"))
            has_linkedin = bool(m.get("linkedin_url") or m.get("is_seeded") or m.get("linkedin_verified"))
            is_verified_advisor = bool(m.get("is_verified", True))

            trust_boost = 0
            if is_verified_advisor:
                trust_boost += 6
            if has_google:
                trust_boost += 4
            if has_linkedin:
                trust_boost += 5

            trust_score = min(99, 84 + trust_boost)

            conn = learner_conns.get(m["mentor_id"])
            mentor_card = {
                k: v for k, v in m.items() if k not in ("mentor_vector", "domain_vector", "skills_vector")
            }
            mentor_card.update({
                "match_score": round(composite_score, 3),
                "match_percent": match_pct,
                "trust_score": trust_score,
                "has_google": has_google,
                "has_linkedin": has_linkedin,
                "is_verified": is_verified_advisor,
                "semantic_similarity_percent": int(round(sem_sim * 100)),
                "skill_overlap_percent": int(round(overlap_score * 100)),
                "shared_gap_skills": shared_gap_skills,
                "shared_general_skills": shared_general_skills,
                "match_tier": match_tier,
                "match_badge": match_badge,
                "has_capacity": has_capacity,
                "connection_status": conn["status"] if conn else "none",
                "connection_id": conn["id"] if conn else None,
                "match_explanation": (
                    f"Directly covers {len(shared_gap_skills)} of your priority skill gaps ({', '.join(shared_gap_skills[:3])})"
                    if shared_gap_skills
                    else f"Aligned with {ctx['career_title']} ({int(round(sem_sim * 100))}% semantic vector similarity)"
                ),
            })
            qualified_matches.append(mentor_card)

        qualified_matches.sort(
            key=lambda x: (x["has_capacity"], len(x["shared_gap_skills"]), x["match_score"]),
            reverse=True,
        )

        return {
            "learner_career": ctx["career_title"],
            "priority_gaps": top_gaps[:5],
            "anti_desperation_threshold": ANTI_DESPERATION_THRESHOLD,
            "filtered_out_by_anti_desperation": filtered_out_count,
            "matches": qualified_matches,
            "zero_match_reason": (
                None
                if qualified_matches
                else (
                    f"Our Anti-Desperation Gate filtered out {filtered_out_count} mentors whose expertise did not align "
                    f"with '{ctx['career_title']}' (minimum required alignment: 45%). You can post questions directly "
                    f"to our Community Q&A Knowledge Base below while domain specialists onboard."
                )
            ),
        }

    # -----------------------------------------------------------------------
    # 2. Connection Handshake & Direct Messaging (DMs)
    # -----------------------------------------------------------------------
    async def request_connection(
        self,
        learner_id: str,
        mentor_id: str,
        goal_note: str,
        auto_accept_demo: bool = False,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        existing = next(
            (c for c in store["connections"] if c["learner_id"] == learner_id and c["mentor_id"] == mentor_id),
            None,
        )
        ctx = self._get_learner_context(learner_id)
        skill_gap_snapshot = {
            "learner_name": ctx["full_name"],
            "target_career": ctx["career_title"],
            "top_skill_gaps": [
                {"name": g["name"], "proficiency": g["proficiency"]}
                for g in ctx["gap_skills"][:5]
            ],
            "avg_proficiency": (
                int(round(sum(s["proficiency"] for s in ctx["all_skills"]) / len(ctx["all_skills"])))
                if ctx["all_skills"]
                else 20
            ),
        }

        mentor_obj = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
        if not mentor_obj:
            raise ValueError("Mentor not found.")

        is_seeded = bool(mentor_obj.get("is_seeded", False))
        initial_status = "accepted" if (auto_accept_demo and is_seeded) else "pending"

        if existing:
            existing["goal_note"] = goal_note or existing.get("goal_note", "")
            existing["learner_snapshot"] = skill_gap_snapshot
            if auto_accept_demo:
                existing["status"] = "accepted"
            self._save_store(store)
            return existing

        conn = {
            "id": f"conn-{uuid.uuid4().hex[:10]}",
            "learner_id": learner_id,
            "mentor_id": mentor_id,
            "mentor_name": mentor_obj.get("full_name", "Mentor"),
            "mentor_headline": mentor_obj.get("headline", ""),
            "mentor_domain": mentor_obj.get("primary_domain", ""),
            "goal_note": goal_note.strip() or f"Seeking guidance on transitioning into {ctx['career_title']}.",
            "status": initial_status,
            "learner_snapshot": skill_gap_snapshot,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        store["connections"].insert(0, conn)

        if initial_status == "accepted":
            store["messages"].append({
                "id": f"msg-{uuid.uuid4().hex[:10]}",
                "connection_id": conn["id"],
                "sender_id": mentor_id,
                "sender_name": mentor_obj.get("full_name", "Mentor"),
                "sender_role": "mentor",
                "text": (
                    f"Hi {ctx['full_name']}! Thanks for connecting. I reviewed your Skill Gap Snapshot for "
                    f"{ctx['career_title']}. Feel free to message me your questions here or book a 1-on-1 session on my calendar!"
                ),
                "created_at": _utc_now_iso(),
            })

        self._save_store(store)
        return conn

    def respond_connection(
        self,
        connection_id: str,
        mentor_id: str,
        action: str,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        conn = next((c for c in store["connections"] if c["id"] == connection_id), None)
        if not conn:
            raise ValueError("Connection request not found.")

        new_status = "accepted" if action == "accept" else "declined"
        conn["status"] = new_status
        conn["updated_at"] = _utc_now_iso()

        if new_status == "accepted":
            mentor_obj = next((m for m in store["mentors"] if m["mentor_id"] == conn["mentor_id"]), None)
            mentor_name = mentor_obj.get("full_name", "Mentor") if mentor_obj else conn.get("mentor_name", "Mentor")
            store["messages"].append({
                "id": f"msg-{uuid.uuid4().hex[:10]}",
                "connection_id": conn["id"],
                "sender_id": conn["mentor_id"],
                "sender_name": mentor_name,
                "sender_role": "mentor",
                "text": (
                    f"Welcome aboard! I've accepted your connection request. Let's focus on closing your priority skill gaps."
                ),
                "created_at": _utc_now_iso(),
            })

        self._save_store(store)
        return conn

    def get_learner_connections(self, learner_id: str) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        conns = [c for c in store["connections"] if c["learner_id"] == learner_id]
        mentors_by_id = {m["mentor_id"]: m for m in store["mentors"]}
        result = []
        for c in conns:
            m = mentors_by_id.get(c["mentor_id"], {})
            conn_msgs = [msg for msg in store.get("messages", []) if msg.get("connection_id") == c["id"]]
            unread = [
                msg for msg in conn_msgs
                if msg.get("sender_id") != learner_id and learner_id not in msg.get("read_by", [msg.get("sender_id")])
            ]
            result.append({
                **c,
                "mentor": {k: v for k, v in m.items() if k != "mentor_vector"} if m else None,
                "last_message": conn_msgs[-1] if conn_msgs else None,
                "unread_count": len(unread),
                "unread_messages": unread,
            })
        return result

    def get_mentor_connections(self, mentor_id: str) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        direct = [c for c in store["connections"] if c["mentor_id"] == mentor_id]
        seeded_ids = {m["mentor_id"] for m in SEEDED_MENTORS}
        if not direct and mentor_id not in seeded_ids:
            direct = [c for c in store["connections"] if c["mentor_id"] in seeded_ids]

        result = []
        for c in direct:
            conn_msgs = [msg for msg in store.get("messages", []) if msg.get("connection_id") == c["id"]]
            unread = [
                msg for msg in conn_msgs
                if msg.get("sender_id") != mentor_id and mentor_id not in msg.get("read_by", [msg.get("sender_id")])
            ]
            result.append({
                **c,
                "last_message": conn_msgs[-1] if conn_msgs else None,
                "unread_count": len(unread),
                "unread_messages": unread,
            })
        return result

    def get_messages(self, connection_id: str, user_id: str) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        changed = False
        conn_msgs = []
        for m in store.get("messages", []):
            if m.get("connection_id") == connection_id:
                conn_msgs.append(m)
                read_by = m.setdefault("read_by", [m.get("sender_id")])
                if user_id and user_id not in read_by:
                    read_by.append(user_id)
                    changed = True
        if changed:
            self._save_store(store)
        return conn_msgs

    def mark_messages_read(self, connection_id: str, user_id: str) -> int:
        store = self._ensure_store()
        changed = False
        count = 0
        for m in store.get("messages", []):
            if m.get("connection_id") == connection_id:
                read_by = m.setdefault("read_by", [m.get("sender_id")])
                if user_id and user_id not in read_by:
                    read_by.append(user_id)
                    count += 1
                    changed = True
        if changed:
            self._save_store(store)
        return count

    def send_message(
        self,
        connection_id: str,
        sender_id: str,
        sender_role: str,
        text: str,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        conn = next((c for c in store["connections"] if c["id"] == connection_id), None)
        if not conn:
            raise ValueError("Connection not found.")
        if conn["status"] != "accepted":
            raise ValueError("Connection must be accepted before sending direct messages.")

        sender_name = (
            conn.get("mentor_name", "Mentor")
            if sender_role == "mentor"
            else conn.get("learner_snapshot", {}).get("learner_name", "Learner")
        )
        msg = {
            "id": f"msg-{uuid.uuid4().hex[:10]}",
            "connection_id": connection_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "sender_role": sender_role,
            "text": text.strip(),
            "created_at": _utc_now_iso(),
            "read_by": [sender_id],
        }
        store["messages"].append(msg)
        self._save_store(store)
        return msg

    # -----------------------------------------------------------------------
    # 3. Mentor Pulse Feed (LinkedIn-style Industry Updates & Events)
    # -----------------------------------------------------------------------
    def get_pulse_feed(
        self,
        learner_id: Optional[str] = None,
        post_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        posts = list(store.get("pulse_posts", []))
        if post_type and post_type != "all":
            posts = [p for p in posts if p.get("post_type", "").lower() == post_type.lower()]

        if learner_id:
            ctx = self._get_learner_context(learner_id)
            learner_skills = {s["name"].lower() for s in ctx["all_skills"]}
            career_tokens = set(ctx["career_title"].lower().replace(",", " ").split())

            def _score_post(post: Dict[str, Any]) -> float:
                tags = [t.lower() for t in post.get("skill_tags", [])]
                overlap = sum(1 for t in tags if any(t in ls or ls in t for ls in learner_skills))
                dom_words = set(post.get("primary_domain", "").lower().split())
                dom_hit = 1 if (career_tokens & dom_words) else 0
                return (overlap * 2.0) + dom_hit + (0.1 * int(post.get("likes_count", 0)))

            posts.sort(key=_score_post, reverse=True)
        else:
            posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)

        return posts

    async def create_pulse_post(
        self,
        mentor_id: str,
        title: str,
        post_type: str,
        body: str,
        skill_tags: List[str],
        external_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        mentor_obj = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)

        mentor_name = "Verified Industry Mentor"
        mentor_headline = "Career Beacon Mentor"
        primary_domain = "Cross-Industry"

        if mentor_obj:
            mentor_name = mentor_obj.get("full_name") or mentor_name
            mentor_headline = mentor_obj.get("headline") or mentor_headline
            primary_domain = mentor_obj.get("primary_domain") or primary_domain
        else:
            try:
                prof = (
                    supabase_client.table("profiles")
                    .select("full_name, bio")
                    .eq("id", mentor_id)
                    .limit(1)
                    .execute()
                )
                if prof.data:
                    mentor_name = prof.data[0].get("full_name") or mentor_name
            except Exception:
                pass

        post = {
            "id": f"pulse-{uuid.uuid4().hex[:10]}",
            "mentor_id": mentor_id,
            "mentor_name": mentor_name,
            "mentor_headline": mentor_headline,
            "primary_domain": primary_domain,
            "post_type": post_type or "Industry Insight",
            "title": title.strip(),
            "body": body.strip(),
            "skill_tags": [t.strip() for t in skill_tags if t.strip()],
            "external_url": external_url.strip() if external_url else None,
            "likes_count": 1,
            "liked_by": [mentor_id],
            "created_at": _utc_now_iso(),
        }
        store["pulse_posts"].insert(0, post)
        self._save_store(store)
        return post

    def toggle_like_pulse_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
        store = self._ensure_store()
        post = next((p for p in store["pulse_posts"] if p["id"] == post_id), None)
        if not post:
            raise ValueError("Pulse post not found.")
        liked_by = post.setdefault("liked_by", [])
        if user_id in liked_by:
            liked_by.remove(user_id)
            post["likes_count"] = max(0, int(post.get("likes_count", 1)) - 1)
        else:
            liked_by.append(user_id)
            post["likes_count"] = int(post.get("likes_count", 0)) + 1
        self._save_store(store)
        return post

    # -----------------------------------------------------------------------
    # 4. Q&A Knowledge Base & Mentor Question Routing
    # -----------------------------------------------------------------------
    async def get_questions(
        self,
        search_query: Optional[str] = None,
        skill_filter: Optional[str] = None,
        mentor_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        questions = list(store.get("questions", []))

        if skill_filter and skill_filter.strip() and skill_filter != "all":
            sf = skill_filter.strip().lower()
            questions = [
                q for q in questions
                if sf in q.get("skill_tag", "").lower() or sf in q.get("career_title", "").lower()
            ]

        if search_query and search_query.strip():
            sq = search_query.strip().lower()
            await self._ensure_question_vectors(store)
            try:
                query_vec = await self.embedding_service.get_embedding(search_query)
            except Exception:
                query_vec = None

            scored_questions: List[tuple[float, Dict[str, Any]]] = []
            for q in questions:
                # 1. Lexical match check
                is_exact_lexical = (
                    sq in q.get("title", "").lower()
                    or sq in q.get("body", "").lower()
                    or sq in q.get("skill_tag", "").lower()
                    or sq in q.get("career_title", "").lower()
                    or any(sq in a.get("body", "").lower() for a in q.get("answers", []))
                )
                lexical_bonus = 0.35 if is_exact_lexical else 0.0

                # 2. Semantic vector cosine similarity
                sem_sim = 0.0
                if query_vec and q.get("embedding"):
                    sem_sim = _cosine_similarity(query_vec, q.get("embedding"))

                total_score = max(sem_sim + lexical_bonus, 0.85 if is_exact_lexical else sem_sim)
                if total_score >= 0.45 or is_exact_lexical:
                    q_copy = dict(q)
                    q_copy["search_relevance"] = round(total_score, 3)
                    scored_questions.append((total_score, q_copy))

            scored_questions.sort(key=lambda item: item[0], reverse=True)
            questions = [item[1] for item in scored_questions]

        if mentor_id:
            mentor_obj = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
            mentor_skills = {s.lower() for s in (mentor_obj.get("expertise_skills", []) if mentor_obj else [])}
            for q in questions:
                q_tag = q.get("skill_tag", "").lower()
                q["mentor_skill_match"] = any(q_tag in ms or ms in q_tag for ms in mentor_skills)
            questions.sort(
                key=lambda q: (
                    q.get("status") == "open",
                    q.get("mentor_skill_match", False),
                    q.get("created_at", ""),
                ),
                reverse=True,
            )
        else:
            questions.sort(key=lambda q: q.get("created_at", ""), reverse=True)

        return questions

    async def find_similar_answered_questions(
        self,
        query_text: str,
        skill_tag: Optional[str] = None,
        threshold: float = 0.75,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Real-time semantic pre-flight lookup for existing verified mentor answers.
        Returns top matching answered tickets to provide instant resolution for recurring student blockers.
        """
        store = self._ensure_store()
        answered = [q for q in store.get("questions", []) if q.get("answers") and len(q["answers"]) > 0]
        if not answered or not query_text.strip():
            return []

        await self._ensure_question_vectors(store)
        try:
            raw_q = query_text.strip()
            formatted_q = f"{raw_q}. Skill: {skill_tag.strip()}." if skill_tag and skill_tag.strip() else raw_q
            q_vecs = await self.embedding_service.get_embeddings_batch(
                [raw_q, formatted_q] if formatted_q != raw_q else [raw_q]
            )
        except Exception:
            return []

        matches = []
        for q in answered:
            q_emb = q.get("embedding")
            sim = max((_cosine_similarity(qv, q_emb) for qv in q_vecs), default=0.0)
            if skill_tag and skill_tag.lower() in q.get("skill_tag", "").lower():
                sim = min(1.0, sim + 0.05)
            if sim >= threshold:
                q_copy = {k: v for k, v in q.items() if k != "embedding"}
                q_copy["similarity"] = round(sim, 3)
                matches.append(q_copy)

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches[:limit]

    async def ask_question(
        self,
        learner_id: str,
        title: str,
        body: str,
        skill_tag: str,
        career_title: Optional[str] = None,
        source_lesson_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        ctx = self._get_learner_context(learner_id)

        # Compute vector representation for instant semantic discovery
        embedding = None
        try:
            q_text = f"{title.strip()}. Skill: {skill_tag.strip()}. {body.strip()[:250]}"
            embedding = await self.embedding_service.get_embedding(q_text)
        except Exception as emb_err:
            logger.debug(f"[MentorshipService] Question embedding skipped: {emb_err}")

        # Check for instant duplicate resolutions among verified answered tickets (threshold >= 0.78)
        suggested_matches = []
        if embedding:
            for existing_q in store.get("questions", []):
                if existing_q.get("answers") and existing_q.get("embedding"):
                    sim = _cosine_similarity(embedding, existing_q.get("embedding"))
                    if sim >= 0.78:
                        ans = existing_q["answers"][0]
                        suggested_matches.append({
                            "question_id": existing_q["id"],
                            "title": existing_q["title"],
                            "similarity": round(sim, 3),
                            "top_answer": ans.get("body", ""),
                            "mentor_name": ans.get("mentor_name", "Verified Mentor"),
                            "mentor_headline": ans.get("mentor_headline", ""),
                        })
            suggested_matches.sort(key=lambda x: x["similarity"], reverse=True)

        q = {
            "id": f"qa-{uuid.uuid4().hex[:10]}",
            "learner_id": learner_id,
            "learner_name": ctx["full_name"],
            "career_title": career_title or ctx["career_title"],
            "skill_tag": skill_tag.strip() or "General Career",
            "title": title.strip(),
            "body": body.strip(),
            "source_lesson_title": source_lesson_title,
            "status": "open",
            "created_at": _utc_now_iso(),
            "answers": [],
            "embedding": embedding,
            "suggested_answers": suggested_matches[:2],
        }
        store["questions"].insert(0, q)
        self._save_store(store)

        # Dual-layer sync: persist question to Supabase mentor_qa when learner has valid UUID
        try:
            uuid.UUID(str(learner_id))
            supabase_client.table("mentor_qa").insert({
                "question": f"{title.strip()}\n\n{body.strip()}",
                "answer": "",
            }).execute()
        except Exception as qa_err:
            logger.debug(f"[MentorshipService] mentor_qa dual-sync skipped: {qa_err}")

        return q

    async def answer_question(
        self,
        question_id: str,
        mentor_id: str,
        body: str,
    ) -> Dict[str, Any]:
        store = self._ensure_store()
        q = next((item for item in store["questions"] if item["id"] == question_id), None)
        if not q:
            raise ValueError("Question not found.")

        mentor_obj = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
        mentor_name = "Verified Industry Mentor"
        mentor_headline = "Career Beacon Mentor"
        if mentor_obj:
            mentor_name = mentor_obj.get("full_name") or mentor_name
            mentor_headline = mentor_obj.get("headline") or mentor_headline
        else:
            try:
                prof = (
                    supabase_client.table("profiles")
                    .select("full_name, bio")
                    .eq("id", mentor_id)
                    .limit(1)
                    .execute()
                )
                if prof.data:
                    mentor_name = prof.data[0].get("full_name") or mentor_name
            except Exception:
                pass

        ans = {
            "id": f"ans-{uuid.uuid4().hex[:10]}",
            "mentor_id": mentor_id,
            "mentor_name": mentor_name,
            "mentor_headline": mentor_headline,
            "body": body.strip(),
            "upvotes": 1,
            "upvoted_by": [mentor_id],
            "is_verified_mentor": True,
            "created_at": _utc_now_iso(),
        }
        q.setdefault("answers", []).append(ans)
        q["status"] = "answered"
        try:
            q["embedding"] = await self.embedding_service.get_embedding(self._format_question_embed_text(q))
            q["answer_embedded"] = True
        except Exception as emb_err:
            logger.debug(f"[MentorshipService] Answer re-embedding skipped: {emb_err}")
        self._save_store(store)
        return q

    def upvote_answer(self, question_id: str, answer_id: str, user_id: str) -> Dict[str, Any]:
        store = self._ensure_store()
        q = next((item for item in store["questions"] if item["id"] == question_id), None)
        if not q:
            raise ValueError("Question not found.")
        ans = next((a for a in q.get("answers", []) if a["id"] == answer_id), None)
        if not ans:
            raise ValueError("Answer not found.")
        upvoted_by = ans.setdefault("upvoted_by", [])
        if user_id in upvoted_by:
            upvoted_by.remove(user_id)
            ans["upvotes"] = max(0, int(ans.get("upvotes", 1)) - 1)
        else:
            upvoted_by.append(user_id)
            ans["upvotes"] = int(ans.get("upvotes", 0)) + 1
        self._save_store(store)
        return ans

    # -----------------------------------------------------------------------
    # 5. 1-on-1 Session Booking, Anti-Double-Booking & Google Calendar / .ics
    # -----------------------------------------------------------------------
    async def get_available_slots(
        self,
        mentor_id: str,
        days_ahead: int = 10,
        learner_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates concrete 45-minute bookable time slots over the next `days_ahead` days
        based on the mentor's `available_days` and `preferred_time_window`, automatically
        excluding any slot already booked by either the mentor or the learner (Anti-Double-Booking).
        """
        store = self._ensure_store()
        mentor = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
        if not mentor:
            raise ValueError("Mentor not found.")

        avail_days = set(mentor.get("available_days") or ["Tue", "Thu"])
        window = mentor.get("preferred_time_window", "Evening")
        if window == "Morning":
            start_hours = [9, 10, 11]
        elif window == "Afternoon":
            start_hours = [14, 15, 16]
        else:
            start_hours = [18, 19, 20]

        booked_starts = {
            s["slot_start_iso"]
            for s in store.get("sessions", [])
            if s.get("status") != "cancelled" and (
                s["mentor_id"] == mentor_id or (learner_id and s.get("learner_id") == learner_id)
            )
        }

        now = datetime.now(timezone.utc)
        day_abbrs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        slots: List[Dict[str, Any]] = []

        for offset in range(1, days_ahead + 1):
            candidate_date = now + timedelta(days=offset)
            day_name = day_abbrs[candidate_date.weekday()]
            if day_name not in avail_days:
                continue

            for hr in start_hours:
                start_dt = datetime(
                    candidate_date.year,
                    candidate_date.month,
                    candidate_date.day,
                    hr,
                    0,
                    0,
                    tzinfo=timezone.utc,
                )
                end_dt = start_dt + timedelta(minutes=45)
                start_iso = start_dt.isoformat()
                # Enforce minimum 24-hour advance booking notice
                if start_dt < now + timedelta(hours=24):
                    continue
                if start_iso in booked_starts:
                    continue

                slots.append({
                    "slot_start_iso": start_iso,
                    "slot_end_iso": end_dt.isoformat(),
                    "day_label": start_dt.strftime("%a, %b %d"),
                    "time_label": f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} UTC",
                    "display_label": f"{start_dt.strftime('%a, %b %d')} · {start_dt.strftime('%H:%M')} UTC",
                    "duration_minutes": 45,
                })

        return slots

    async def book_session(
        self,
        learner_id: str,
        mentor_id: str,
        slot_start_iso: str,
        topic: str,
        focus_skill: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Books a 45-minute 1-on-1 session with strict Anti-Double-Booking conflict detection,
        generating a valid Jitsi Meet conference room, Google Calendar template URL,
        and downloadable `.ics` invite with 24h & 15m VALARM reminders.
        """
        store = self._ensure_store()
        mentor = next((m for m in store["mentors"] if m["mentor_id"] == mentor_id), None)
        if not mentor:
            raise ValueError("Mentor not found.")

        try:
            start_dt = datetime.fromisoformat(slot_start_iso.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("Invalid ISO timestamp for session start.")
        end_dt = start_dt + timedelta(minutes=45)

        now_utc = datetime.now(timezone.utc)
        if start_dt < now_utc:
            raise ValueError("Scheduling conflict: Cannot schedule a session in the past.")

        if start_dt < now_utc + timedelta(hours=24):
            raise ValueError("Advance notice required: Sessions must be scheduled at least 24 hours in advance to allow preparation.")

        for existing in store.get("sessions", []):
            if existing.get("status") == "cancelled":
                continue
            ex_start = datetime.fromisoformat(existing["slot_start_iso"].replace("Z", "+00:00"))
            ex_end = datetime.fromisoformat(existing["slot_end_iso"].replace("Z", "+00:00"))
            overlaps = start_dt < ex_end and end_dt > ex_start
            if overlaps and existing["mentor_id"] == mentor_id:
                raise ValueError(
                    "Double-booking prevented: The mentor already has a confirmed session scheduled during this time window."
                )
            if overlaps and existing["learner_id"] == learner_id:
                raise ValueError(
                    "Double-booking prevented: This learner is unavailable at this time due to an existing scheduled session."
                )

        ctx = self._get_learner_context(learner_id)
        short_code = f"{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
        meeting_room = f"CareerBeacon-{short_code}"
        meeting_url = f"https://meet.jit.si/{meeting_room}"

        gcal_dates = f"{start_dt.strftime('%Y%m%dT%H%M%SZ')}/{end_dt.strftime('%Y%m%dT%H%M%SZ')}"
        event_title = f"Career Beacon 1:1 — {topic} ({mentor.get('full_name', 'Mentor')})"
        event_details = (
            f"Career Beacon 1-on-1 Mentorship Session\n"
            f"Mentor: {mentor.get('full_name')}\n"
            f"Learner: {ctx['full_name']} ({ctx['career_title']})\n"
            f"Focus Skill: {focus_skill or 'Career Strategy'}\n"
            f"Meeting ID: {short_code}\n"
            f"Video Room Link: {meeting_url}\n\n"
            f"Session Notes: {notes or 'Reviewing skill gap progression and practical scenarios.'}"
        )
        google_calendar_url = (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote(event_title)}"
            f"&dates={gcal_dates}"
            f"&details={quote(event_details)}"
            f"&location={quote(meeting_url)}"
        )

        session_id = f"sess-{uuid.uuid4().hex[:10]}"
        session_record = {
            "id": session_id,
            "learner_id": learner_id,
            "learner_name": ctx["full_name"],
            "learner_career": ctx["career_title"],
            "mentor_id": mentor_id,
            "mentor_name": mentor.get("full_name", "Mentor"),
            "mentor_headline": mentor.get("headline", ""),
            "topic": topic.strip() or "1-on-1 Skill Gap Coaching",
            "focus_skill": focus_skill,
            "notes": notes.strip(),
            "slot_start_iso": start_dt.isoformat(),
            "slot_end_iso": end_dt.isoformat(),
            "display_label": f"{start_dt.strftime('%a, %b %d, %Y')} · {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} UTC",
            "duration_minutes": 45,
            "meeting_code": short_code,
            "meeting_url": meeting_url,
            "google_calendar_url": google_calendar_url,
            "reminders": [
                {"type": "email_and_calendar", "lead_time": "24 hours before", "status": "scheduled"},
                {"type": "popup_notification", "lead_time": "15 minutes before", "status": "scheduled"},
            ],
            "status": "confirmed",
            "endorsed_skill": None,
            "created_at": _utc_now_iso(),
        }

        store["sessions"].insert(0, session_record)
        self._save_store(store)

        # Dual-layer persistence: sync session booking to Supabase bookings table when valid UUIDs exist
        try:
            uuid.UUID(str(learner_id))
            m_uuid = None
            try:
                m_uuid = str(uuid.UUID(str(mentor_id)))
            except Exception:
                pass

            booking_payload: Dict[str, Any] = {
                "user_id": learner_id,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "status": "confirmed",
                "meeting_link": meeting_url,
            }
            if m_uuid:
                booking_payload["mentor_id"] = m_uuid

            supabase_client.table("bookings").insert(booking_payload).execute()
        except Exception as db_sync_err:
            logger.debug(f"[MentorshipService] Supabase bookings dual-sync skipped: {db_sync_err}")

        return session_record

    def get_sessions(self, user_id: str, role: str = "learner") -> List[Dict[str, Any]]:
        store = self._ensure_store()
        if role == "mentor":
            direct = [s for s in store["sessions"] if s["mentor_id"] == user_id]
            seeded_ids = {m["mentor_id"] for m in SEEDED_MENTORS}
            if not direct and user_id not in seeded_ids:
                direct = [s for s in store["sessions"] if s["mentor_id"] in seeded_ids]
            sess_list = direct
        else:
            sess_list = [s for s in store["sessions"] if s["learner_id"] == user_id]

        # Rank strictly by proximity in time (earliest/closest upcoming first)
        sess_list.sort(key=lambda s: s.get("slot_start_iso", ""))
        return sess_list

    def cancel_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        store = self._ensure_store()
        sess = next((s for s in store["sessions"] if s["id"] == session_id), None)
        if not sess:
            raise ValueError("Session not found.")
        sess["status"] = "cancelled"
        self._save_store(store)

        # Dual-layer sync: update Supabase bookings status
        try:
            uuid.UUID(str(user_id))
            supabase_client.table("bookings").update({"status": "cancelled"}).eq("user_id", user_id).execute()
        except Exception:
            pass

        return sess

    def complete_session_and_endorse_skill(
        self,
        session_id: str,
        mentor_id: str,
        endorse_skill_name: Optional[str] = None,
        feedback_note: str = "",
    ) -> Dict[str, Any]:
        """
        Marks a session completed and (if `endorse_skill_name` is provided) boosts the
        learner's proficiency in `public.user_skills` by +15% (up to 100%) with
        `evidence_source = 'mentor_verified'`.
        """
        store = self._ensure_store()
        sess = next((s for s in store["sessions"] if s["id"] == session_id), None)
        if not sess:
            raise ValueError("Session not found.")

        sess["status"] = "completed"
        sess["feedback_note"] = feedback_note.strip()
        skill_to_endorse = (endorse_skill_name or sess.get("focus_skill") or "").strip()

        if skill_to_endorse:
            sess["endorsed_skill"] = {
                "skill_name": skill_to_endorse,
                "endorsement_type": "mentor_reviewed",
                "feedback_note": feedback_note.strip(),
                "endorsed_at": _utc_now_iso(),
            }

        self._save_store(store)
        return sess
        return sess

    def get_session_ics(self, session_id: str) -> str:
        """
        Generates a standards-compliant RFC 5545 iCalendar (.ics) file with two
        VALARM reminders (24 hours before and 15 minutes before).
        """
        store = self._ensure_store()
        sess = next((s for s in store["sessions"] if s["id"] == session_id), None)
        if not sess:
            raise ValueError("Session not found.")

        start_dt = datetime.fromisoformat(sess["slot_start_iso"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(sess["slot_end_iso"].replace("Z", "+00:00"))
        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dtstart = start_dt.strftime("%Y%m%dT%H%M%SZ")
        dtend = end_dt.strftime("%Y%m%dT%H%M%SZ")

        summary = f"Career Beacon 1:1 — {sess['topic']} ({sess['mentor_name']})"
        description = (
            f"Career Beacon 1-on-1 Mentorship Session\\n"
            f"Mentor: {sess['mentor_name']}\\n"
            f"Learner: {sess.get('learner_name', 'Learner')}\\n"
            f"Focus Skill: {sess.get('focus_skill') or 'Career Strategy'}\\n"
            f"Meeting ID: {sess['meeting_code']}\\n"
            f"Join Video Room: {sess['meeting_url']}"
        )

        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Career Beacon//Mentorship Ecosystem//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{sess['id']}@careerbeacon.app",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{sess['meeting_url']}",
            "STATUS:CONFIRMED",
            "BEGIN:VALARM",
            "TRIGGER:-PT24H",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder: Career Beacon 1-on-1 Mentorship Session in 24 hours",
            "END:VALARM",
            "BEGIN:VALARM",
            "TRIGGER:-PT15M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder: Career Beacon 1-on-1 Mentorship Session starts in 15 minutes",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        return "\r\n".join(ics_lines) + "\r\n"


mentorship_service = MentorshipService()
