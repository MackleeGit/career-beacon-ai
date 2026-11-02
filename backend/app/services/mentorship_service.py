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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

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
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (n1 * n2)))


# ---------------------------------------------------------------------------
# Pre-Seeded Cross-Industry Reference Mentors (6 Domains)
# ---------------------------------------------------------------------------
SEEDED_MENTORS: List[Dict[str, Any]] = [
    {
        "mentor_id": "seed-mentor-swe",
        "full_name": "Dr. Marcus Vance",
        "primary_domain": "Software Architecture & Full-Stack",
        "headline": "Principal Distributed Systems Architect | Ex-Cloud Infrastructure Lead",
        "bio": "14+ years designing fault-tolerant microservices, PostgreSQL/SQL indexing strategies, REST/GraphQL APIs, and coaching software engineers through system design and production readiness.",
        "expertise_skills": [
            "Python", "SQL", "PostgreSQL", "System Design", "Docker",
            "REST APIs", "Software Architecture", "Git", "JavaScript", "React"
        ],
        "weekly_hours": 6,
        "available_days": ["Mon", "Wed", "Fri"],
        "preferred_time_window": "Evening",
        "max_mentees": 5,
        "active_mentees_count": 2,
        "verified_sessions_count": 28,
        "avg_rating": 4.9,
        "is_seeded": True,
    },
    {
        "mentor_id": "seed-mentor-data",
        "full_name": "Elena Rostova",
        "primary_domain": "AI, Machine Learning & Data Science",
        "headline": "Lead Machine Learning & Analytics Engineer | NLP & Predictive Modeling",
        "bio": "Specializes in production ML pipelines, SQL/Pandas data wrangling, statistical hypothesis testing, vector embeddings, and helping data analysts transition into applied AI roles.",
        "expertise_skills": [
            "Machine Learning", "Data Analysis", "Python", "SQL",
            "Statistics", "Pandas", "Deep Learning", "Data Visualization", "NLP"
        ],
        "weekly_hours": 5,
        "available_days": ["Tue", "Thu", "Sat"],
        "preferred_time_window": "Afternoon",
        "max_mentees": 4,
        "active_mentees_count": 1,
        "verified_sessions_count": 19,
        "avg_rating": 4.95,
        "is_seeded": True,
    },
    {
        "mentor_id": "seed-mentor-fin",
        "full_name": "Jonathan Sterling, CFA",
        "primary_domain": "Finance, Accounting & Quantitative Analysis",
        "headline": "VP of Corporate Finance & Risk Advisory | Chartered Financial Analyst",
        "bio": "Mentors aspiring financial analysts, accountants, and auditors in 3-statement financial modeling, GAAP/IFRS compliance, budgeting, variance analysis, and valuation.",
        "expertise_skills": [
            "Financial Analysis", "Accounting", "Financial Modeling", "Budgeting",
            "Risk Management", "Excel", "Auditing", "Corporate Finance", "Economics"
        ],
        "weekly_hours": 4,
        "available_days": ["Tue", "Thu"],
        "preferred_time_window": "Evening",
        "max_mentees": 5,
        "active_mentees_count": 2,
        "verified_sessions_count": 22,
        "avg_rating": 4.85,
        "is_seeded": True,
    },
    {
        "mentor_id": "seed-mentor-health",
        "full_name": "Sarah Jenkins, RN, MSN",
        "primary_domain": "Healthcare, Nursing & Clinical Practice",
        "headline": "Clinical Nurse Educator & Patient Safety Director | Acute Care Specialist",
        "bio": "12 years in acute clinical care, triage protocols, clinical documentation, pharmacology safety, and mentoring healthcare practitioners and clinical coordinators.",
        "expertise_skills": [
            "Patient Care", "Clinical Assessment", "Medical Terminology",
            "Infection Control", "Healthcare Compliance", "Triage", "Emergency Care"
        ],
        "weekly_hours": 5,
        "available_days": ["Mon", "Thu", "Sat"],
        "preferred_time_window": "Morning",
        "max_mentees": 4,
        "active_mentees_count": 1,
        "verified_sessions_count": 16,
        "avg_rating": 5.0,
        "is_seeded": True,
    },
    {
        "mentor_id": "seed-mentor-eng",
        "full_name": "Engr. David Okafor, PE",
        "primary_domain": "Civil, Mechanical & Petroleum Engineering",
        "headline": "Senior Structural & Energy Systems Engineer | Project Management Professional",
        "bio": "Guides civil, mechanical, and petroleum engineers in CAD/structural analysis, reservoir & fluid mechanics, OSHA field safety, and capital project execution.",
        "expertise_skills": [
            "Engineering Design", "Project Management", "AutoCAD", "Structural Analysis",
            "Fluid Mechanics", "Quality Assurance", "Operations Management", "Safety Compliance"
        ],
        "weekly_hours": 4,
        "available_days": ["Wed", "Sat"],
        "preferred_time_window": "Afternoon",
        "max_mentees": 4,
        "active_mentees_count": 1,
        "verified_sessions_count": 14,
        "avg_rating": 4.88,
        "is_seeded": True,
    },
    {
        "mentor_id": "seed-mentor-culinary",
        "full_name": "Chef Antoine Moreau",
        "primary_domain": "Culinary Arts, Hospitality & Skilled Trades",
        "headline": "Executive Culinary Director & Multi-Unit Kitchen Operations Specialist",
        "bio": "20 years leading commercial kitchens and quick-service food operations. Mentors cooks, chefs, and hospitality leads in HACCP food safety, prep station throughput, inventory cost control, and menu execution.",
        "expertise_skills": [
            "Food Safety & HACCP", "Kitchen Operations", "Food Preparation",
            "Inventory Management", "Menu Costing", "Sanitation", "Quality Control", "Customer Service"
        ],
        "weekly_hours": 6,
        "available_days": ["Mon", "Tue", "Fri"],
        "preferred_time_window": "Afternoon",
        "max_mentees": 6,
        "active_mentees_count": 2,
        "verified_sessions_count": 31,
        "avg_rating": 4.92,
        "is_seeded": True,
    },
]

SEEDED_PULSE_POSTS: List[Dict[str, Any]] = [
    {
        "id": "pulse-seed-1",
        "mentor_id": "seed-mentor-swe",
        "mentor_name": "Dr. Marcus Vance",
        "mentor_headline": "Principal Distributed Systems Architect",
        "primary_domain": "Software Architecture & Full-Stack",
        "post_type": "Industry Insight",
        "title": "Why Composite B-Tree Indexes Fail Silently in High-Write PostgreSQL Workloads",
        "body": (
            "When optimizing slow SQL queries, junior engineers often add single-column indexes on every WHERE clause column. "
            "In production, column order inside a composite index (Leftmost Prefix Rule) dictates whether the query planner performs an Index Seek or falls back to a Sequential Scan.\n\n"
            "Rule of thumb for your next architecture review: place equality predicates (=) first, and range predicates (>, <, BETWEEN) last."
        ),
        "skill_tags": ["SQL", "PostgreSQL", "System Design", "Software Architecture"],
        "external_url": "https://use-the-index-luke.com/",
        "likes_count": 18,
        "liked_by": [],
        "created_at": "2026-10-30T14:20:00+00:00",
    },
    {
        "id": "pulse-seed-2",
        "mentor_id": "seed-mentor-fin",
        "mentor_name": "Jonathan Sterling, CFA",
        "mentor_headline": "VP of Corporate Finance & Risk Advisory",
        "primary_domain": "Finance, Accounting & Quantitative Analysis",
        "post_type": "Career & Hiring Advice",
        "title": "The #1 Working Capital Mistake in Entry-Level Financial Modeling Tests",
        "body": (
            "In 80% of financial analyst case interviews I grade, candidates link Net Income to the Cash Flow Statement properly but invert the cash impact of Accounts Receivable (AR) and Inventory.\n\n"
            "Remember: an increase in an operating asset (AR or Inventory) is a CASH OUTFLOW, while an increase in Accounts Payable (AP) is a CASH INFLOW. Always run a balance sheet check row (Assets - Liabilities - Equity = 0) before submitting!"
        ),
        "skill_tags": ["Financial Modeling", "Accounting", "Financial Analysis", "Corporate Finance"],
        "external_url": None,
        "likes_count": 14,
        "liked_by": [],
        "created_at": "2026-10-30T18:00:00+00:00",
    },
    {
        "id": "pulse-seed-3",
        "mentor_id": "seed-mentor-culinary",
        "mentor_name": "Chef Antoine Moreau",
        "mentor_headline": "Executive Culinary Director & Kitchen Operations Specialist",
        "primary_domain": "Culinary Arts, Hospitality & Skilled Trades",
        "post_type": "Industry Insight",
        "title": "Mastering the Two-Stage Cooling Protocol & Station Mise en Place Under Rush Load",
        "body": (
            "Whether you run a high-volume fast-food line or a brigade kitchen, two habits separate top operators from chaotic shifts:\n"
            "1. Strict Temperature Danger Zone control (cooling cooked batches from 135°F to 70°F within 2 hours, and down to 41°F within 4 hours).\n"
            "2. FIFO (First-In, First-Out) pan rotation so prep waste stays under 3.5%."
        ),
        "skill_tags": ["Food Safety & HACCP", "Kitchen Operations", "Food Preparation", "Sanitation"],
        "external_url": None,
        "likes_count": 21,
        "liked_by": [],
        "created_at": "2026-10-31T08:15:00+00:00",
    },
    {
        "id": "pulse-seed-4",
        "mentor_id": "seed-mentor-data",
        "mentor_name": "Elena Rostova",
        "mentor_headline": "Lead Machine Learning & Analytics Engineer",
        "primary_domain": "AI, Machine Learning & Data Science",
        "post_type": "Event / Webinar",
        "title": "Live Workshop This Thursday: Preventing Data Leakage in Time-Series & Tabular ML",
        "body": (
            "Hosting a 45-minute open workshop this Thursday at 17:00 UTC covering target encoding pitfalls, "
            "temporal train/validation splits, and how to defend your evaluation metrics in technical interviews."
        ),
        "skill_tags": ["Machine Learning", "Data Analysis", "Statistics", "Python"],
        "external_url": "https://scikit-learn.org/stable/common_pitfalls.html",
        "likes_count": 25,
        "liked_by": [],
        "created_at": "2026-10-31T10:30:00+00:00",
    },
]

SEEDED_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "qa-seed-1",
        "learner_id": "demo-learner-1",
        "learner_name": "Alex Rivera",
        "career_title": "Software Developer",
        "skill_tag": "SQL",
        "title": "When should I use a CTE (WITH clause) versus a temporary indexed table in PostgreSQL?",
        "body": "While doing the SQL micro-learning sprint, I noticed CTEs make complex aggregations readable, but how do they behave on multi-million row joins?",
        "source_lesson_title": "PostgreSQL Query Optimization & Indexing",
        "status": "answered",
        "created_at": "2026-10-29T16:00:00+00:00",
        "answers": [
            {
                "id": "ans-seed-1",
                "mentor_id": "seed-mentor-swe",
                "mentor_name": "Dr. Marcus Vance",
                "mentor_headline": "Principal Distributed Systems Architect",
                "body": (
                    "Great question! Since PostgreSQL 12+, non-recursive CTEs referenced only once are inlined by default (acting like subqueries so index pushdown works). "
                    "However, if a CTE is referenced multiple times and materialized in memory without indexes, a Temporary Table with an explicit CREATE INDEX on the join key is significantly faster for 5M+ rows."
                ),
                "upvotes": 12,
                "upvoted_by": [],
                "is_verified_mentor": True,
                "created_at": "2026-10-29T17:15:00+00:00",
            }
        ],
    },
    {
        "id": "qa-seed-2",
        "learner_id": "demo-learner-2",
        "learner_name": "Maya Lin",
        "career_title": "Financial Analyst",
        "skill_tag": "Financial Modeling",
        "title": "How do you justify WACC terminal growth rate assumptions during an valuation defense?",
        "body": "If a company is growing revenue at 18% over the 5-year forecast window, why must the perpetuity growth rate (g) in the Gordon Growth Model stay below 2.5%–3.0%?",
        "source_lesson_title": "Discounted Cash Flow (DCF) & Terminal Value",
        "status": "answered",
        "created_at": "2026-10-30T11:10:00+00:00",
        "answers": [
            {
                "id": "ans-seed-2",
                "mentor_id": "seed-mentor-fin",
                "mentor_name": "Jonathan Sterling, CFA",
                "mentor_headline": "VP of Corporate Finance & Risk Advisory",
                "body": (
                    "Because a terminal growth rate applies forever (to infinity). Mathematically, if a single firm grew faster than nominal global GDP (typically 2.5%–3.0%) forever, "
                    "that single company would eventually become larger than the entire global economy. If the company still has high growth in Year 5, extend your explicit forecast to a 10-year two-stage DCF before applying terminal value."
                ),
                "upvotes": 9,
                "upvoted_by": [],
                "is_verified_mentor": True,
                "created_at": "2026-10-30T12:05:00+00:00",
            }
        ],
    },
    {
        "id": "qa-seed-3",
        "learner_id": "demo-learner-3",
        "learner_name": "Devon Brooks",
        "career_title": "Cooks, Fast Food",
        "skill_tag": "Food Safety & HACCP",
        "title": "What is the exact corrective action if a hot-holding line drops below 135°F (57°C) during peak lunch?",
        "body": "If our steam table thermometer reads 124°F during a rush check, can we just turn up the dial on the holding well, or do we have to reheat on the range?",
        "source_lesson_title": "HACCP Critical Control Points in Commercial Kitchens",
        "status": "answered",
        "created_at": "2026-10-31T09:00:00+00:00",
        "answers": [
            {
                "id": "ans-seed-3",
                "mentor_id": "seed-mentor-culinary",
                "mentor_name": "Chef Antoine Moreau",
                "mentor_headline": "Executive Culinary Director & Kitchen Operations Specialist",
                "body": (
                    "Never use a hot-holding steam table to reheat food! Holding wells are engineered only to maintain temperature, not bring food rapidly through the danger zone. "
                    "Corrective action: If it has been under 135°F for less than 2 hours, rapidly reheat the batch on a stove/oven to 165°F (74°C) for at least 15 seconds before returning it to a verified 135°F+ holding well."
                ),
                "upvotes": 15,
                "upvoted_by": [],
                "is_verified_mentor": True,
                "created_at": "2026-10-31T09:40:00+00:00",
            }
        ],
    },
]


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
        """Lazily computes and caches 384-d vectors for any mentor missing `mentor_vector`."""
        updated = False
        for m in store.get("mentors", []):
            if not m.get("mentor_vector"):
                skills_str = ", ".join(m.get("expertise_skills", []))
                text = (
                    f"Domain: {m.get('primary_domain', '')}. "
                    f"Headline: {m.get('headline', '')}. "
                    f"Specialization: {m.get('bio', '')}. "
                    f"Core Skills: {skills_str}."
                )
                try:
                    vec = await self.embedding_service.get_embedding(text)
                    m["mentor_vector"] = vec
                    updated = True
                except Exception as err:
                    print(f"[MentorshipService] Failed to embed mentor {m.get('mentor_id')}: {err}")
        if updated:
            self._save_store(store)

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
        text = (
            f"Domain: {primary_domain}. "
            f"Headline: {headline}. "
            f"Specialization: {bio}. "
            f"Core Skills: {skills_str}."
        )
        try:
            vec = await self.embedding_service.get_embedding(text)
        except Exception:
            vec = None

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
                "mentor_vector": vec or existing.get("mentor_vector"),
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
                "mentor_vector": vec,
            }
            store["mentors"].insert(0, record)

        self._save_store(store)
        return {k: v for k, v in record.items() if k != "mentor_vector"}

    async def get_all_mentors(self) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        await self._ensure_mentor_vectors(store)

        try:
            db_mentors = supabase_client.table("mentors").select("*").execute()
            known_ids = {m["mentor_id"] for m in store["mentors"]}
            for row in db_mentors.data or []:
                mid = row.get("profile_id") or row.get("mentor_id") or row.get("id")
                if mid and mid not in known_ids:
                    prof = (
                        supabase_client.table("profiles")
                        .select("full_name, bio")
                        .eq("id", mid)
                        .limit(1)
                        .execute()
                    )
                    p_data = prof.data[0] if prof.data else {}
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
        need_summary = (
            f"Target Career: {ctx['career_title']}. "
            f"Description: {ctx['career_description']}. "
            f"Priority Skill Gaps: {', '.join(top_gaps if top_gaps else all_skill_names)}."
        )
        try:
            learner_vec = await self.embedding_service.get_embedding(need_summary)
        except Exception:
            learner_vec = None

        learner_conns = {
            c["mentor_id"]: c
            for c in store.get("connections", [])
            if c["learner_id"] == learner_id
        }

        qualified_matches: List[Dict[str, Any]] = []
        filtered_out_count = 0

        career_lower = ctx["career_title"].lower()
        gap_lower_map = {g["name"].lower(): g["name"] for g in ctx["gap_skills"]}
        all_lower_map = {s["name"].lower(): s["name"] for s in ctx["all_skills"]}

        for m in mentors:
            if m["mentor_id"] == learner_id:
                continue

            active_count = int(m.get("active_mentees_count", 0))
            max_cap = int(m.get("max_mentees", 5))
            has_capacity = active_count < max_cap

            sem_sim = _cosine_similarity(learner_vec, m.get("mentor_vector"))

            mentor_skills = m.get("expertise_skills", [])
            shared_gap_skills: List[str] = []
            shared_general_skills: List[str] = []

            for m_sk in mentor_skills:
                m_low = m_sk.lower()
                matched_gap = next(
                    (orig for k_low, orig in gap_lower_map.items() if m_low in k_low or k_low in m_low),
                    None,
                )
                if matched_gap and matched_gap not in shared_gap_skills:
                    shared_gap_skills.append(matched_gap)
                else:
                    matched_any = next(
                        (orig for k_low, orig in all_lower_map.items() if m_low in k_low or k_low in m_low),
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
            domain_score = 1.0 if token_hits > 0 else (0.5 if shared_gap_skills else 0.0)

            composite_score = (0.55 * sem_sim) + (0.30 * overlap_score) + (0.15 * domain_score)
            match_pct = int(round(composite_score * 100))

            passes_anti_desperation = (
                composite_score >= ANTI_DESPERATION_THRESHOLD
                or len(shared_gap_skills) >= 1
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
                k: v for k, v in m.items() if k != "mentor_vector"
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
            result.append({
                **c,
                "mentor": {k: v for k, v in m.items() if k != "mentor_vector"} if m else None,
            })
        return result

    def get_mentor_connections(self, mentor_id: str) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        direct = [c for c in store["connections"] if c["mentor_id"] == mentor_id]
        seeded_ids = {m["mentor_id"] for m in SEEDED_MENTORS}
        if not direct and mentor_id not in seeded_ids:
            direct = [c for c in store["connections"] if c["mentor_id"] in seeded_ids]
        return direct

    def get_messages(self, connection_id: str, user_id: str) -> List[Dict[str, Any]]:
        store = self._ensure_store()
        return [m for m in store["messages"] if m["connection_id"] == connection_id]

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
            questions = [
                q for q in questions
                if sq in q.get("title", "").lower()
                or sq in q.get("body", "").lower()
                or sq in q.get("skill_tag", "").lower()
                or sq in q.get("career_title", "").lower()
                or any(sq in a.get("body", "").lower() for a in q.get("answers", []))
            ]

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

    def ask_question(
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
        }
        store["questions"].insert(0, q)
        self._save_store(store)
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
    async def get_available_slots(self, mentor_id: str, days_ahead: int = 10) -> List[Dict[str, Any]]:
        """
        Generates concrete 45-minute bookable time slots over the next `days_ahead` days
        based on the mentor's `available_days` and `preferred_time_window`, automatically
        excluding any slot already booked (Anti-Double-Booking).
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
            if s["mentor_id"] == mentor_id and s.get("status") != "cancelled"
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
        return session_record

    def get_sessions(self, user_id: str, role: str = "learner") -> List[Dict[str, Any]]:
        store = self._ensure_store()
        if role == "mentor":
            direct = [s for s in store["sessions"] if s["mentor_id"] == user_id]
            seeded_ids = {m["mentor_id"] for m in SEEDED_MENTORS}
            if not direct and user_id not in seeded_ids:
                direct = [s for s in store["sessions"] if s["mentor_id"] in seeded_ids]
            return direct
        return [s for s in store["sessions"] if s["learner_id"] == user_id]

    def cancel_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        store = self._ensure_store()
        sess = next((s for s in store["sessions"] if s["id"] == session_id), None)
        if not sess:
            raise ValueError("Session not found.")
        sess["status"] = "cancelled"
        self._save_store(store)
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
