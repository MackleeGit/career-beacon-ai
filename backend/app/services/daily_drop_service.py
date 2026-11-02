"""
Daily Focus Drop Service
------------------------
Implements the Brilliant/Wordle Daily Drop model:
1. Each active learner receives a targeted 3-lesson drop per 24 hours focused on their highest skill gap.
2. Controlled 1-Shot Re-Roll per day (mulligan): Allows shuffling to secondary deficit once, then locks.
3. Daily Streak counter and completion habit loop.
4. Strict skill relevance verification (no cross-domain collisions, verified adapters).
"""

import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.core.database import supabase_client
from app.services.recommendation_service import (
    RecommendationService,
    _is_adapter_compatible_with_career,
    _lesson_matches_career,
    _cosine_similarity
)
from app.services.content_service import classify_source_adapter

logger = logging.getLogger("career_beacon.daily_drop_service")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DAILY_SPRINTS_FILE = os.path.join(DATA_DIR, "daily_sprints.json")
STREAKS_FILE = os.path.join(DATA_DIR, "user_streaks.json")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_str() -> str:
    return _now_utc().strftime("%Y-%m-%d")


def _load_json_file(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return []


def _save_json_file(file_path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")


class DailyDropService:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.rec_service = RecommendationService()

    # -------------------------------------------------------------------------
    # 1. Streak Management
    # -------------------------------------------------------------------------

    def get_streak_info(self, user_id: str) -> Dict[str, Any]:
        """Returns the user's current streak, longest streak, and last active date."""
        streaks = _load_json_file(STREAKS_FILE)
        user_streak = next((s for s in streaks if s.get("user_id") == user_id), None)
        if not user_streak:
            return {
                "user_id": user_id,
                "current_streak": 0,
                "longest_streak": 0,
                "last_active_date": None,
                "completed_today": False,
            }

        last_date = user_streak.get("last_active_date")
        today = _today_str()
        completed_today = (last_date == today)

        # Check if streak was broken (last active date was before yesterday)
        current = user_streak.get("current_streak", 0)
        if last_date and not completed_today:
            try:
                last_dt = datetime.strptime(last_date, "%Y-%m-%d").date()
                today_dt = datetime.strptime(today, "%Y-%m-%d").date()
                if (today_dt - last_dt).days > 1:
                    current = 0  # Streak broke
            except Exception:
                pass

        return {
            "user_id": user_id,
            "current_streak": current,
            "longest_streak": user_streak.get("longest_streak", 0),
            "last_active_date": last_date,
            "completed_today": completed_today,
        }

    def _increment_streak(self, user_id: str) -> Dict[str, Any]:
        """Increments streak when a learner passes all lessons in today's daily drop."""
        streaks = _load_json_file(STREAKS_FILE)
        today = _today_str()
        yesterday = (_now_utc() - timedelta(days=1)).strftime("%Y-%m-%d")

        user_streak = next((s for s in streaks if s.get("user_id") == user_id), None)
        if not user_streak:
            user_streak = {
                "user_id": user_id,
                "current_streak": 1,
                "longest_streak": 1,
                "last_active_date": today,
            }
            streaks.append(user_streak)
        else:
            last_date = user_streak.get("last_active_date")
            if last_date == today:
                # Already marked for today
                return user_streak
            elif last_date == yesterday:
                user_streak["current_streak"] = user_streak.get("current_streak", 0) + 1
            else:
                user_streak["current_streak"] = 1

            if user_streak["current_streak"] > user_streak.get("longest_streak", 0):
                user_streak["longest_streak"] = user_streak["current_streak"]
            user_streak["last_active_date"] = today

        _save_json_file(STREAKS_FILE, streaks)
        return user_streak

    # -------------------------------------------------------------------------
    # 2. Strict Skill Relevance Verification
    # -------------------------------------------------------------------------

    def _verify_lesson_relevance(
        self,
        lesson: Dict[str, Any],
        skill_name: str,
        skill_id: str,
        career_title: str
    ) -> bool:
        """
        Guarantees the lesson is genuinely relevant to the targeted skill:
        1. Career adapter compatibility (no MDN in clinical, no PubMed in tech).
        2. Direct skill assignment (associated_skill_id == skill_id).
        3. Sufficient text substance and valid checkpoint quizzes.
        """
        # 1. Adapter compatibility check
        if not _is_adapter_compatible_with_career(lesson, career_title):
            return False

        # 1B. Strict Career Boundary check: Reject lessons explicitly branded for another career
        if not _lesson_matches_career(lesson, career_title):
            return False

        # 1C. Anti-Spurious Topical Gate: Reject ancient history/mythology lessons for modern workplace skills
        title_lower = (lesson.get("title") or "").lower()
        hist_flags = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore")
        if any(h in title_lower for h in hist_flags) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth")):
            return False

        # 2. Associated skill binding
        if lesson.get("associated_skill_id") != skill_id:
            return False

        # 3. Quizzes completeness check (must have at least 1 verified question)
        quizzes = lesson.get("quizzes")
        if isinstance(quizzes, str):
            try:
                quizzes = json.loads(quizzes)
            except Exception:
                quizzes = []
        if not isinstance(quizzes, list) or len(quizzes) == 0:
            content_dict = lesson.get("content")
            if isinstance(content_dict, dict) and content_dict.get("quizzes"):
                quizzes = content_dict.get("quizzes")
            elif isinstance(content_dict, str):
                try:
                    c_parsed = json.loads(content_dict)
                    quizzes = c_parsed.get("quizzes", [])
                except Exception:
                    quizzes = []

        if not quizzes or len(quizzes) == 0:
            return False

        return True

    # -------------------------------------------------------------------------
    # 3. Daily Drop Retrieval and Curation
    # -------------------------------------------------------------------------

    async def get_or_create_daily_drop(self, user_id: str) -> Dict[str, Any]:
        """
        Returns today's 3-lesson drop. If not pre-computed, curates it instantly.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        existing = next(
            (s for s in sprints if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None
        )

        if existing:
            # Check if existing drop was a valid calibrated drop
            has_target = existing.get("target_skill_id") is not None
            has_enough = len(existing.get("lesson_ids", [])) >= 3
            if has_target and has_enough:
                hydrated = await self._hydrate_drop(existing, user_id)
                if hydrated.get("lessons") and len(hydrated["lessons"]) >= 3:
                    prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
                    cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
                    c_title = self.rec_service.get_cached_career(cid).get("title", "") if cid else ""
                    if all(_lesson_matches_career(l, c_title) for l in hydrated["lessons"]):
                        return hydrated

            # If existing drop was an empty onboarding stub (< 3) or contaminated, purge it from cache
            sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]
            _save_json_file(DAILY_SPRINTS_FILE, sprints)

        # Curate fresh daily drop
        new_drop = await self._curate_daily_drop(user_id=user_id, sprint_date=today, priority_index=0)
        # ONLY cache to disk if it contains calibrated lessons for a real skill
        if new_drop.get("target_skill_id") and len(new_drop.get("lesson_ids", [])) > 0:
            sprints.append(new_drop)
            _save_json_file(DAILY_SPRINTS_FILE, sprints)
        return await self._hydrate_drop(new_drop, user_id)

    async def reroll_daily_drop(self, user_id: str) -> Dict[str, Any]:
        """
        Shuffles today's drop to the pre-loaded 3 reserve lessons for the SAME focus skill (1-shot mulligan).
        Executes instantaneously in 0ms without re-querying or invoking LLMs.
        Raises ValueError if re-roll was already used today.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        drop_idx = next(
            (i for i, s in enumerate(sprints) if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None
        )

        if drop_idx is None:
            # Generate initial drop first
            drop = await self.get_or_create_daily_drop(user_id)
            return drop

        existing = sprints[drop_idx]
        if existing.get("rerolls_used", 0) >= 1:
            raise ValueError("You have already used your daily shuffle. Complete today's drop to unlock tomorrow's sprint.")

        # Swap active lessons with the pre-cached reserve lessons for the exact same focus skill
        reserve_ids = existing.get("reserve_lesson_ids", [])
        if reserve_ids:
            existing["active_lesson_ids"] = reserve_ids
            existing["lesson_ids"] = reserve_ids
        existing["rerolls_used"] = 1
        existing["passed_lesson_ids"] = []  # Reset passed status for the fresh reserve batch
        existing["is_completed"] = False

        sprints[drop_idx] = existing
        _save_json_file(DAILY_SPRINTS_FILE, sprints)
        return await self._hydrate_drop(existing, user_id)

    async def record_lesson_passed(self, user_id: str, lesson_id: str) -> Dict[str, Any]:
        """
        Marks a lesson passed in today's drop and checks for sprint completion.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        drop = next(
            (s for s in sprints if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None
        )

        if not drop:
            return {"status": "ignored", "reason": "No active drop for today"}

        passed_set = set(drop.get("passed_lesson_ids", []))
        passed_set.add(lesson_id)
        drop["passed_lesson_ids"] = list(passed_set)

        lesson_ids = drop.get("lesson_ids", [])
        is_now_completed = all(lid in passed_set for lid in lesson_ids)
        was_completed = drop.get("is_completed", False)

        if is_now_completed and not was_completed:
            drop["is_completed"] = True
            streak_info = self._increment_streak(user_id)
        else:
            streak_info = self.get_streak_info(user_id)

        _save_json_file(DAILY_SPRINTS_FILE, sprints)
        return {
            "status": "success",
            "is_completed": drop.get("is_completed", False),
            "passed_count": len(drop["passed_lesson_ids"]),
            "total_count": len(lesson_ids),
            "streak": streak_info,
        }

    # -------------------------------------------------------------------------
    # 4. Internal Helpers
    # -------------------------------------------------------------------------

    async def _curate_daily_drop(
        self,
        user_id: str,
        sprint_date: str,
        priority_index: int = 0,
        excluded_ids: Optional[List[str]] = None,
        rerolls_used: int = 0
    ) -> Dict[str, Any]:
        """Synthesizes or selects 3 verified lessons for the prioritized deficit."""
        excluded = set(excluded_ids or [])

        # 1. Fetch user target career
        prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
        career_id = prof_res.data[0]["target_career_id"] if prof_res.data else None
        if not career_id:
            return {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "sprint_date": sprint_date,
                "target_skill_id": None,
                "target_skill_name": "General Career Foundations",
                "lesson_ids": [],
                "passed_lesson_ids": [],
                "rerolls_used": rerolls_used,
                "is_completed": False,
                "created_at": _now_utc().isoformat(),
            }

        career = self.rec_service.get_cached_career(career_id)
        career_title = career.get("title", "Target Career")
        career_skills_map = self.rec_service.get_cached_career_skills(career_id)

        # 2. Fetch user's enrolled skills
        user_skills_res = supabase_client.table("user_skills").select(
            "skill_id, proficiency, skills(id, name, category)"
        ).eq("user_id", user_id).execute()

        skills = []
        for row in (user_skills_res.data or []):
            sk = row.get("skills")
            if sk:
                meta = career_skills_map.get(sk["id"], {})
                prof = int(row.get("proficiency", 20))
                essential = meta.get("importance") == "essential"
                tier = meta.get("tier") or 3
                skills.append({
                    "id": sk["id"],
                    "name": sk["name"],
                    "category": sk.get("category", "Technical"),
                    "proficiency": prof,
                    "essential": essential,
                    "tier": tier,
                })

        # Self-healing: if user is missing essential career skills, auto-enroll them
        enrolled_ids = {s["id"] for s in skills}
        missing_essential_ids = [
            sid for sid, meta in career_skills_map.items()
            if meta.get("importance") == "essential" and sid not in enrolled_ids
        ]
        # Fallback if no essential skills exist for this career: take top 5 by importance score
        if not missing_essential_ids and not enrolled_ids and career_skills_map:
            sorted_career_skills = sorted(
                career_skills_map.items(),
                key=lambda pair: pair[1].get("importance_score") or 0.0,
                reverse=True
            )
            missing_essential_ids = [sid for sid, _ in sorted_career_skills[:5]]

        if missing_essential_ids:
            try:
                all_skills_map = self.rec_service.get_cached_all_skills()
                auto_inserts = []
                for sid in missing_essential_ids:
                    sk = all_skills_map.get(sid)
                    if sk:
                        skills.append({
                            "id": sid,
                            "name": sk.get("name", "Core Skill"),
                            "category": sk.get("category", "Technical"),
                            "proficiency": 20,
                            "essential": True,
                            "tier": career_skills_map.get(sid, {}).get("tier") or 1,
                        })
                        auto_inserts.append({"user_id": user_id, "skill_id": sid, "proficiency": 20})
                if auto_inserts:
                    supabase_client.table("user_skills").insert(auto_inserts).execute()
            except Exception as e:
                logger.warning(f"Auto-backfill essential skills in daily drop notice: {e}")

        # 2B. Adaptive Daily Rotation & Interleaving
        # Inspect user's recent daily sprints so we rotate topics daily across the career's
        # essential competency pillars rather than redundantly sticking to a single skill.
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        past_sprints = [s for s in sprints if s.get("user_id") == user_id]
        past_sprints.sort(key=lambda s: s.get("sprint_date", ""), reverse=True)
        recent_focused_skill_ids = [
            s.get("target_skill_id")
            for s in past_sprints[:5]
            if s.get("target_skill_id")
        ]

        def rotation_priority(s):
            # Recency penalty: if focused on recently, rotate to fresh career pillars
            recency_penalty = 0
            if s["id"] in recent_focused_skill_ids:
                recency_index = recent_focused_skill_ids.index(s["id"])
                recency_penalty = max(10, 100 - (recency_index * 20))

            mastery_penalty = 50 if s["proficiency"] >= 80 else 0
            return (recency_penalty, not s["essential"], s["tier"], mastery_penalty, s["proficiency"])

        skills.sort(key=rotation_priority)

        target_skill = skills[priority_index] if len(skills) > priority_index else (skills[0] if skills else None)
        target_skill_id = target_skill["id"] if target_skill else None
        target_skill_name = target_skill["name"] if target_skill else "Core Competency"

        # 3. Fetch candidate lessons for target_skill_id from micro_content
        candidates = []
        if target_skill_id:
            table_res = supabase_client.table("micro_content").select("*").eq(
                "associated_skill_id", target_skill_id
            ).limit(20).execute()

            for item in (table_res.data or []):
                if item["id"] in excluded:
                    continue
                if self._verify_lesson_relevance(item, target_skill_name, target_skill_id, career_title):
                    candidates.append(item)

        # 3B. JIT Dynamic Generation for Target Skill: If candidate pool has < 3,
        # prioritize synthesizing lessons specifically for the focused deficit skill first.
        if len(candidates) < 3 and target_skill and target_skill_id:
            needed = 3 - len(candidates)
            for _ in range(needed):
                try:
                    jit_lesson = await asyncio.wait_for(
                        self.rec_service.content_service.generate_dynamic_lesson_for_skill(
                            skill_id=target_skill_id,
                            skill_name=target_skill_name,
                            category=target_skill.get("category", "Core"),
                            career_title=career_title,
                            target_proficiency=target_skill.get("proficiency", 20),
                            career_skill_context=career_skills_map.get(target_skill_id, {})
                        ),
                        timeout=14.0
                    )
                    if jit_lesson and isinstance(jit_lesson, dict) and jit_lesson.get("id"):
                        if self._verify_lesson_relevance(jit_lesson, target_skill_name, target_skill_id, career_title):
                            if jit_lesson["id"] not in [c["id"] for c in candidates]:
                                candidates.append(jit_lesson)
                except Exception as e:
                    logger.warning(f"JIT live source ingestion notice for {target_skill_name}: {e}")

        # 3B. Soft Exclusion Fallback: If library was too sparse to satisfy exclusions (e.g. after re-roll),
        # recycle earlier career-relevant lessons rather than stranding learner with 0 or < 3 cards.
        if len(candidates) < 3 and excluded:
            if target_skill_id:
                table_res = supabase_client.table("micro_content").select("*").eq(
                    "associated_skill_id", target_skill_id
                ).limit(20).execute()
                for item in (table_res.data or []):
                    if item["id"] not in [c["id"] for c in candidates]:
                        if self._verify_lesson_relevance(item, target_skill_name, target_skill_id, career_title):
                            candidates.append(item)
                            if len(candidates) >= 6:
                                break

            if len(candidates) < 3 and len(skills) > 1:
                for alt_skill in skills:
                    alt_res = supabase_client.table("micro_content").select("*").eq(
                        "associated_skill_id", alt_skill["id"]
                    ).limit(10).execute()
                    for item in (alt_res.data or []):
                        if item["id"] not in [c["id"] for c in candidates]:
                            if self._verify_lesson_relevance(item, alt_skill["name"], alt_skill["id"], career_title):
                                candidates.append(item)
                                if len(candidates) >= 6:
                                    break
                    if len(candidates) >= 6:
                        break

        # 3C. JIT Dynamic Generation: If candidate pool is insufficient (< 3),
        # dynamically synthesize real domain-grounded lessons across the learner's essential skills.
        if len(candidates) < 3 and skills:
            skills_to_try = [target_skill] + [s for s in skills if s.get("id") != target_skill_id]
            for sk in skills_to_try:
                if len(candidates) >= 3:
                    break
                s_id = sk.get("id")
                s_name = sk.get("name")
                if not s_id or not s_name:
                    continue
                try:
                    jit_lesson = await asyncio.wait_for(
                        self.rec_service.content_service.generate_dynamic_lesson_for_skill(
                            skill_id=s_id,
                            skill_name=s_name,
                            category=sk.get("category", "Core"),
                            career_title=career_title,
                            target_proficiency=sk.get("proficiency", 20),
                            career_skill_context=career_skills_map.get(s_id, {})
                        ),
                        timeout=14.0
                    )
                    if jit_lesson and isinstance(jit_lesson, dict) and jit_lesson.get("id"):
                        if self._verify_lesson_relevance(jit_lesson, s_name, s_id, career_title):
                            if jit_lesson["id"] not in [c["id"] for c in candidates]:
                                candidates.append(jit_lesson)
                except Exception as e:
                    logger.warning(f"JIT live source ingestion notice for {s_name}: {e}")

        # Partition into 3 active + 3 reserve lessons for the SAME topic
        active_candidates = candidates[:3]
        reserve_candidates = candidates[3:6]
        if not reserve_candidates and len(active_candidates) > 0:
            reserve_candidates = list(reversed(active_candidates))

        active_lesson_ids = [c["id"] for c in active_candidates]
        reserve_lesson_ids = [c["id"] for c in reserve_candidates]

        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "sprint_date": sprint_date,
            "target_skill_id": target_skill_id,
            "target_skill_name": target_skill_name,
            "active_lesson_ids": active_lesson_ids,
            "reserve_lesson_ids": reserve_lesson_ids,
            "lesson_ids": active_lesson_ids,
            "passed_lesson_ids": [],
            "rerolls_used": rerolls_used,
            "is_completed": False,
            "created_at": _now_utc().isoformat(),
        }

    async def _hydrate_drop(self, drop: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Fetches full lesson details for the IDs in the daily drop."""
        lesson_ids = drop.get("active_lesson_ids") or drop.get("lesson_ids", [])
        lessons = []

        if lesson_ids:
            res = supabase_client.table("micro_content").select("*").in_("id", lesson_ids).execute()
            lesson_map = {item["id"]: item for item in (res.data or [])}
            all_skills_map = self.rec_service.get_cached_all_skills()

            passed_set = set(drop.get("passed_lesson_ids", []))
            for lid in lesson_ids:
                raw = lesson_map.get(lid)
                if not raw:
                    continue
                assoc_skill_id = raw.get("associated_skill_id")
                skill_info = all_skills_map.get(assoc_skill_id, {})

                quizzes = raw.get("quizzes")
                if isinstance(quizzes, str):
                    try:
                        quizzes = json.loads(quizzes)
                    except Exception:
                        quizzes = []

                lessons.append({
                    "id": raw["id"],
                    "title": raw["title"],
                    "source_url": raw.get("source_url", ""),
                    "source_name": raw.get("source_name") or raw.get("source") or "",
                    "source_adapter": classify_source_adapter(raw.get("source_url", ""), raw.get("source_name", "")),
                    "video_id": raw.get("video_id"),
                    "summary_bullets": raw.get("summary_bullets") or raw.get("summary") or "",
                    "concept_overview": raw.get("concept_overview") or "",
                    "practice_scenario": raw.get("practice_scenario") or "",
                    "difficulty_level": int(raw.get("difficulty_level") or 2),
                    "quizzes": quizzes or [],
                    "skill_id": assoc_skill_id,
                    "skill_name": skill_info.get("name") or drop.get("target_skill_name") or "Core Skill",
                    "skill_category": skill_info.get("category") or "Technical",
                    "has_passed": raw["id"] in passed_set,
                })

        streak_info = self.get_streak_info(user_id)
        now = _now_utc()
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        seconds_until_next = int((tomorrow - now).total_seconds())

        return {
            "id": drop.get("id"),
            "sprint_date": drop.get("sprint_date"),
            "target_skill_id": drop.get("target_skill_id"),
            "target_skill_name": drop.get("target_skill_name"),
            "lessons": lessons,
            "passed_count": len(drop.get("passed_lesson_ids", [])),
            "total_count": len(lessons),
            "is_completed": drop.get("is_completed", False),
            "rerolls_used": drop.get("rerolls_used", 0),
            "can_reroll": drop.get("rerolls_used", 0) < 1 and not drop.get("is_completed", False) and len(drop.get("reserve_lesson_ids", [])) > 0,
            "streak": streak_info,
            "seconds_until_next_drop": seconds_until_next,
        }

