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
    _source_quality_multiplier,
    _cosine_similarity
)
from app.services.content_service import classify_source_adapter, hydrate_micro_content_row

logger = logging.getLogger("career_beacon.daily_drop_service")

DAILY_DROP_SIZE = 3
RESERVE_DROP_SIZE = 3

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
        career_title: str,
        onet_soc_code: Optional[str] = None,
    ) -> bool:
        """
        Guarantees the lesson is genuinely relevant to the targeted skill:
        1. Career adapter compatibility (no MDN in clinical, no PubMed in tech).
        2. Direct skill assignment (associated_skill_id == skill_id).
        3. Sufficient text substance and valid checkpoint quizzes.
        """
        # 1. Adapter compatibility check
        if not _is_adapter_compatible_with_career(lesson, career_title, onet_soc_code=onet_soc_code):
            return False

        # 1B. Career & Domain Boundary check: Allow shared canonical skills across sibling careers in the same domain
        if not _lesson_matches_career(
            lesson, career_title, onet_soc_code=onet_soc_code, enrolled_skill_ids={skill_id}
        ):
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
        Returns today's 5-lesson Daily Drop. If not pre-computed, curates it and records impressions.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        existing = next(
            (s for s in sprints if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None
        )

        if existing:
            has_target = existing.get("target_skill_id") is not None
            has_enough = len(existing.get("lesson_ids", [])) >= 3
            if has_target and has_enough:
                hydrated = await self._hydrate_drop(existing, user_id)
                if hydrated.get("lessons") and len(hydrated["lessons"]) >= 3:
                    prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
                    cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
                    career_obj = self.rec_service.get_cached_career(cid) if cid else {}
                    c_title = career_obj.get("title", "")
                    c_soc = career_obj.get("onet_soc_code")
                    if all(
                        _lesson_matches_career(
                            l,
                            c_title,
                            onet_soc_code=c_soc,
                            enrolled_skill_ids={l.get("skill_id") or l.get("associated_skill_id")},
                        )
                        for l in hydrated["lessons"]
                    ):
                        return hydrated

            sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]
            _save_json_file(DAILY_SPRINTS_FILE, sprints)

        new_drop = await self._curate_daily_drop(user_id=user_id, sprint_date=today, priority_index=0)
        if new_drop.get("target_skill_id") and len(new_drop.get("lesson_ids", [])) > 0:
            sprints.append(new_drop)
            _save_json_file(DAILY_SPRINTS_FILE, sprints)
            self.rec_service.history_service.record_impressions(user_id, new_drop.get("lesson_ids", []))
        return await self._hydrate_drop(new_drop, user_id)

    async def trigger_daily_worker(self, user_id: str, force_fresh: bool = True) -> Dict[str, Any]:
        """
        Debug & On-Demand Daily Update Worker:
        Clears today's cached sprint for the user, resets the daily reroll lock (`rerolls_used = 0`),
        runs the multi-skill 5-primary + 5-reserve ingestion & ranking pipeline, and returns the hydrated drop.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        old_sprint = next(
            (s for s in sprints if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None,
        )
        prev_ids = list(old_sprint.get("active_lesson_ids", [])) if old_sprint else []

        sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]
        _save_json_file(DAILY_SPRINTS_FILE, sprints)

        new_drop = await self._curate_daily_drop(
            user_id=user_id,
            sprint_date=today,
            priority_index=0,
            excluded_ids=prev_ids if not force_fresh else [],
            rerolls_used=0,
            force_worker_topup=force_fresh,
        )
        if new_drop.get("target_skill_id") and len(new_drop.get("lesson_ids", [])) > 0:
            sprints.append(new_drop)
            _save_json_file(DAILY_SPRINTS_FILE, sprints)
            self.rec_service.history_service.record_impressions(user_id, new_drop.get("lesson_ids", []))
        return await self._hydrate_drop(new_drop, user_id)

    async def reroll_daily_drop(self, user_id: str) -> Dict[str, Any]:
        """
        Shuffles today's drop to the 5 reserve lessons (1-shot free reroll).
        If the pre-cached reserve set has fewer than 5 lessons, tops up from secondary priority skills.
        Raises ValueError if re-roll was already used today.
        """
        today = _today_str()
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        drop_idx = next(
            (i for i, s in enumerate(sprints) if s.get("user_id") == user_id and s.get("sprint_date") == today),
            None
        )

        if drop_idx is None:
            drop = await self.get_or_create_daily_drop(user_id)
            return drop

        existing = sprints[drop_idx]
        if existing.get("rerolls_used", 0) >= 1:
            raise ValueError("You have already used your daily shuffle. Complete today's drop to unlock tomorrow's sprint.")

        active_ids = list(existing.get("active_lesson_ids") or existing.get("lesson_ids") or [])
        reserve_ids = [lid for lid in existing.get("reserve_lesson_ids", []) if lid not in active_ids]

        # If reserve pool is smaller than DAILY_DROP_SIZE, curate a fresh second set excluding the first set
        if len(reserve_ids) < DAILY_DROP_SIZE:
            second_drop = await self._curate_daily_drop(
                user_id=user_id,
                sprint_date=today,
                priority_index=1,
                excluded_ids=active_ids,
                rerolls_used=1,
            )
            for lid in second_drop.get("active_lesson_ids", []):
                if lid not in reserve_ids and lid not in active_ids:
                    reserve_ids.append(lid)
                    if len(reserve_ids) >= DAILY_DROP_SIZE:
                        break
            if second_drop.get("target_skill_name"):
                existing["target_skill_name"] = second_drop["target_skill_name"]
                existing["target_skill_id"] = second_drop.get("target_skill_id")
                existing["focus_skill_names"] = second_drop.get("focus_skill_names", [])

        # If still fewer than DAILY_DROP_SIZE, find any compatible domain lessons in reservoir excluding active_ids
        if len(reserve_ids) < DAILY_DROP_SIZE:
            prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
            cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
            career_obj = self.rec_service.get_cached_career(cid) if cid else {}
            c_title = career_obj.get("title", "")
            c_soc = career_obj.get("onet_soc_code")

            all_res = supabase_client.table("micro_content").select("*").order("source_trust_score", desc=True).limit(60).execute()
            for cand in (all_res.data or []):
                cand_id = cand.get("id")
                if not cand_id or cand_id in active_ids or cand_id in reserve_ids:
                    continue
                if _lesson_matches_career(cand, c_title, onet_soc_code=c_soc):
                    reserve_ids.append(cand_id)
                    if len(reserve_ids) >= DAILY_DROP_SIZE:
                        break

        if reserve_ids:
            existing["active_lesson_ids"] = reserve_ids[:DAILY_DROP_SIZE]
            existing["lesson_ids"] = reserve_ids[:DAILY_DROP_SIZE]
            self.rec_service.history_service.record_impressions(user_id, existing["lesson_ids"])

        existing["rerolls_used"] = 1
        existing["passed_lesson_ids"] = []
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
        is_now_completed = bool(lesson_ids) and all(lid in passed_set for lid in lesson_ids)
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
        rerolls_used: int = 0,
        force_worker_topup: bool = False,
    ) -> Dict[str, Any]:
        """
        Synthesizes and ranks 5 primary + 5 reserve verified lessons interleaved across
        the learner's top priority skill gaps, adjusted for proficiency and learning history.
        """
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
                "focus_skill_names": [],
                "lesson_ids": [],
                "passed_lesson_ids": [],
                "rerolls_used": rerolls_used,
                "is_completed": False,
                "created_at": _now_utc().isoformat(),
            }

        career = self.rec_service.get_cached_career(career_id)
        career_title = career.get("title", "Target Career")
        onet_soc_code = career.get("onet_soc_code")
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

        # 2B. Adaptive Daily Rotation & Multi-Skill Priority Ordering
        sprints = _load_json_file(DAILY_SPRINTS_FILE)
        past_sprints = [s for s in sprints if s.get("user_id") == user_id]
        past_sprints.sort(key=lambda s: s.get("sprint_date", ""), reverse=True)
        recent_focused_skill_ids = [
            s.get("target_skill_id")
            for s in past_sprints[:5]
            if s.get("target_skill_id")
        ]

        def rotation_priority(s):
            recency_penalty = 0
            if s["id"] in recent_focused_skill_ids:
                recency_index = recent_focused_skill_ids.index(s["id"])
                recency_penalty = max(10, 100 - (recency_index * 20))
            mastery_penalty = 50 if s["proficiency"] >= 80 else 0
            return (recency_penalty, not s["essential"], s["tier"], mastery_penalty, s["proficiency"])

        skills.sort(key=rotation_priority)
        if priority_index > 0 and len(skills) > 1:
            skills = skills[priority_index:] + skills[:priority_index]

        focus_skills = skills[:5] if skills else []
        target_skill = focus_skills[0] if focus_skills else None
        target_skill_id = target_skill["id"] if target_skill else None
        target_skill_name = target_skill["name"] if target_skill else "Core Competency"
        focus_skill_ids = [s["id"] for s in focus_skills if s.get("id")]
        skill_by_id = {s["id"]: s for s in skills if s.get("id")}

        # 3. Fetch existing verified candidate lessons across the learner's focus skills
        candidates = []
        seen_cand_ids = set()
        if focus_skill_ids:
            table_res = supabase_client.table("micro_content").select("*").in_(
                "associated_skill_id", focus_skill_ids
            ).limit(60).execute()

            for item in (table_res.data or []):
                lid = item.get("id")
                sid = item.get("associated_skill_id")
                sk_obj = skill_by_id.get(sid)
                if not lid or lid in excluded or lid in seen_cand_ids or not sk_obj:
                    continue
                # Never re-serve a lesson the learner has already passed
                if self.rec_service.history_service.has_passed_lesson(user_id, lid):
                    continue
                if self._verify_lesson_relevance(item, sk_obj["name"], sid, career_title, onet_soc_code=onet_soc_code):
                    candidates.append(item)
                    seen_cand_ids.add(lid)

        # 3B. Multi-Source Worker / Ingestion Acceleration
        # Ensure we have a rich pool across the learner's focus skills using strict domain-compatible adapters
        target_pool_size = (DAILY_DROP_SIZE + RESERVE_DROP_SIZE) if force_worker_topup else DAILY_DROP_SIZE
        if len(candidates) < target_pool_size and focus_skills:
            by_skill_count: Dict[str, int] = {}
            for c in candidates:
                sid = c.get("associated_skill_id")
                by_skill_count[sid] = by_skill_count.get(sid, 0) + 1

            # Domain-strict adapter mapping (zero cross-domain contamination)
            from app.services.recommendation_service import resolve_career_domain_standard
            user_domain = resolve_career_domain_standard(career_title, onet_soc_code)
            if user_domain == "tech":
                non_video_adapters = ["structured_tutorial", "owasp", "open_textbook", "mdn", "arxiv"]
            elif user_domain in ("healthcare", "science"):
                non_video_adapters = ["clinical_science", "open_textbook", "structured_tutorial"]
            elif user_domain in ("business_finance", "business_admin"):
                non_video_adapters = ["finance", "structured_tutorial", "open_textbook"]
            elif user_domain == "engineering":
                non_video_adapters = ["structured_tutorial", "open_textbook", "arxiv", "osha"]
            else:
                non_video_adapters = ["structured_tutorial", "open_textbook"]

            gen_specs = []
            for idx, sk in enumerate(focus_skills):
                sid = sk["id"]
                have = by_skill_count.get(sid, 0)
                want = 2 if idx < 3 else 1
                for slot in range(max(0, want - have)):
                    pref = ["youtube"] if (idx + slot) % 2 == 0 else non_video_adapters
                    gen_specs.append((sk, pref))
                if len(gen_specs) >= (6 if force_worker_topup else 2):
                    break

            sem = asyncio.Semaphore(2)

            async def _gen_one(sk_item: Dict[str, Any], pref_adapters: List[str]):
                async with sem:
                    try:
                        return await asyncio.wait_for(
                            self.rec_service.content_service.generate_dynamic_lesson_for_skill(
                                skill_id=sk_item["id"],
                                skill_name=sk_item["name"],
                                category=sk_item.get("category", "Core"),
                                career_title=career_title,
                                target_proficiency=sk_item.get("proficiency", 20),
                                career_skill_context=career_skills_map.get(sk_item["id"], {}),
                                preferred_adapters=pref_adapters,
                                onet_soc_code=onet_soc_code,
                            ),
                            timeout=8.0 if force_worker_topup else 4.0,
                        )
                    except Exception as e:
                        logger.warning(f"Daily Drop worker ingestion notice for {sk_item.get('name')}: {e}")
                        return None

            if gen_specs:
                gen_results = await asyncio.gather(*(_gen_one(sk, pr) for sk, pr in gen_specs), return_exceptions=True)
                for res_lesson in gen_results:
                    if isinstance(res_lesson, dict) and res_lesson.get("id"):
                        lid = res_lesson["id"]
                        sid = res_lesson.get("associated_skill_id")
                        sk_obj = skill_by_id.get(sid) or target_skill
                        if lid not in seen_cand_ids and sk_obj:
                            if self._verify_lesson_relevance(res_lesson, sk_obj["name"], sid, career_title, onet_soc_code=onet_soc_code):
                                candidates.append(res_lesson)
                                seen_cand_ids.add(lid)

        # 3C. Soft Exclusion Fallback if pool is still sparse (< DAILY_DROP_SIZE)
        if len(candidates) < DAILY_DROP_SIZE and excluded and focus_skill_ids:
            table_res = supabase_client.table("micro_content").select("*").in_(
                "associated_skill_id", focus_skill_ids
            ).limit(40).execute()
            for item in (table_res.data or []):
                lid = item.get("id")
                sid = item.get("associated_skill_id")
                sk_obj = skill_by_id.get(sid)
                if not lid or lid in seen_cand_ids or not sk_obj:
                    continue
                if self.rec_service.history_service.has_passed_lesson(user_id, lid):
                    continue
                if self._verify_lesson_relevance(item, sk_obj["name"], sid, career_title, onet_soc_code=onet_soc_code):
                    candidates.append(item)
                    seen_cand_ids.add(lid)
                    if len(candidates) >= (DAILY_DROP_SIZE + RESERVE_DROP_SIZE):
                        break

        # 3C-2. Multi-Competency Career Reservoir Top-up: strictly guarantee DAILY_DROP_SIZE (5 lessons)
        if len(candidates) < (DAILY_DROP_SIZE + RESERVE_DROP_SIZE):
            other_skill_ids = [s["id"] for s in skills if s.get("id") and s["id"] not in seen_cand_ids]
            if other_skill_ids:
                other_res = supabase_client.table("micro_content").select("*").in_(
                    "associated_skill_id", other_skill_ids
                ).order("source_trust_score", desc=True).limit(30).execute()
                all_skills_map = self.rec_service.get_cached_all_skills()
                for item in (other_res.data or []):
                    lid = item.get("id")
                    sid = item.get("associated_skill_id")
                    sk_obj = skill_by_id.get(sid) or all_skills_map.get(sid)
                    if not lid or lid in seen_cand_ids or not sk_obj:
                        continue
                    if self.rec_service.history_service.has_passed_lesson(user_id, lid):
                        continue
                    if not self._verify_lesson_relevance(item, sk_obj.get("name", ""), sid, career_title, onet_soc_code=onet_soc_code):
                        continue
                    candidates.append(item)
                    seen_cand_ids.add(lid)
                    if len(candidates) >= (DAILY_DROP_SIZE + RESERVE_DROP_SIZE):
                        break

        # 3C-3. Sibling Career In Same Cognitive Field: NEVER allow cross-domain contamination
        if len(candidates) < (DAILY_DROP_SIZE + RESERVE_DROP_SIZE):
            from app.services.recommendation_service import resolve_career_domain_standard
            user_domain = resolve_career_domain_standard(career_title, onet_soc_code)
            all_skills_map = self.rec_service.get_cached_all_skills()

            field_res = supabase_client.table("micro_content").select("*").order("source_trust_score", desc=True).limit(60).execute()
            for item in (field_res.data or []):
                lid = item.get("id")
                sid = item.get("associated_skill_id")
                sk_name = (all_skills_map.get(sid) or {}).get("name", "")
                if not lid or lid in seen_cand_ids or lid in excluded:
                    continue
                if self.rec_service.history_service.has_passed_lesson(user_id, lid):
                    continue
                # Strict domain boundary verification
                if not _is_adapter_compatible_with_career(item, career_title, onet_soc_code=onet_soc_code):
                    continue
                if not _lesson_matches_career(item, career_title, onet_soc_code=onet_soc_code, enrolled_skill_ids=set(s["id"] for s in skills)):
                    continue
                # Fail-safe anti-contamination guard
                title_lower = (item.get("title") or "").lower()
                url_lower = (item.get("source_url") or "").lower()
                med_flags = ("vital signs", "pharmacology", "nclex", "nursing", "patient care", "specimen collection", "clinical diagnosis", "dosages", "hospital")
                if user_domain != "healthcare" and any(m in title_lower or m in url_lower for m in med_flags):
                    continue
                candidates.append(item)
                seen_cand_ids.add(lid)
                if len(candidates) >= (DAILY_DROP_SIZE + RESERVE_DROP_SIZE):
                    break

        # 3D. Stage 2 Hybrid RRF + Proficiency Difficulty Fit + History Cooldown Re-Ranking
        if len(candidates) > 1 and focus_skills:
            try:
                all_skills_map = self.rec_service.get_cached_all_skills()
                for item in candidates:
                    if not item.get("skill_name"):
                        sid = item.get("associated_skill_id")
                        item["skill_name"] = (all_skills_map.get(sid) or skill_by_id.get(sid) or {}).get("name", "")

                per_skill_queries = [
                    f"Lesson: {s['name']}. Target Skill: {s['name']} ({s.get('category') or 'Core'}). Career: {career_title}."
                    for s in focus_skills
                ]
                skill_vecs = await self.rec_service.embedding_service.get_embeddings_batch(per_skill_queries)
                skill_vec_map = {s["id"]: v for s, v in zip(focus_skills, skill_vecs)}

                for item in candidates:
                    sid = item.get("associated_skill_id")
                    q_v = skill_vec_map.get(sid) or (skill_vecs[0] if skill_vecs else None)
                    sim = _cosine_similarity(q_v, item.get("embedding")) if q_v else None
                    item["similarity"] = float(sim) if sim is not None else 0.72

                frontier_q = f"Curriculum and practical instructional concepts for {career_title}."
                candidates = self.rec_service._apply_reciprocal_rank_fusion(
                    candidates, frontier_q, [s["name"] for s in focus_skills]
                )
                user_activity_map = self.rec_service.history_service.get_user_activity_map(user_id)

                def _daily_drop_rank_score(item: Dict[str, Any]) -> float:
                    base_sim = float(item.get("hybrid_score") or item.get("similarity") or 0.72)
                    sid = item.get("associated_skill_id")
                    sk_obj = skill_by_id.get(sid) or target_skill or {}
                    s_prof = int(sk_obj.get("proficiency", 20))
                    expected_diff = max(1, min(5, round(s_prof / 22.0) + 1))
                    item_diff = int(item.get("difficulty_level") or 2)
                    if item_diff > (expected_diff + 1):
                        diff_mult = max(0.45, 1.0 - 0.25 * (item_diff - expected_diff))
                    elif item_diff <= expected_diff:
                        diff_mult = 1.08
                    else:
                        diff_mult = 1.0

                    src_mult = _source_quality_multiplier(item, career_title)

                    # History cooldown: penalize lessons seen on previous days that were ignored
                    act = user_activity_map.get(item.get("id"), {})
                    times_rec = int(act.get("times_recommended") or 0)
                    opened = bool(act.get("opened_at"))
                    if opened:
                        act_mult = 1.10  # Boost in-progress lessons opened by learner
                    elif times_rec >= 1:
                        act_mult = max(0.50, 0.82 ** min(times_rec, 4))
                    else:
                        act_mult = 1.05  # Fresh unseen lesson bonus

                    return base_sim * diff_mult * src_mult * act_mult

                candidates.sort(key=_daily_drop_rank_score, reverse=True)
            except Exception as rank_err:
                logger.debug(f"Daily drop candidate ranking fallback: {rank_err}")

        # 3E. Interleaved Multi-Skill & Source-Diverse Partitioning (3 Active + 3 Reserve)
        # Prevent any single skill from monopolizing active slots (1 per skill when multiple skills exist)
        active_candidates: List[Dict[str, Any]] = []
        reserve_candidates: List[Dict[str, Any]] = []
        skill_counts_active: Dict[str, int] = {}
        max_per_skill = 1 if len({c.get("associated_skill_id") for c in candidates}) >= 3 else 2

        for cand in candidates:
            sid = cand.get("associated_skill_id")
            if len(active_candidates) < DAILY_DROP_SIZE and skill_counts_active.get(sid, 0) < max_per_skill:
                active_candidates.append(cand)
                skill_counts_active[sid] = skill_counts_active.get(sid, 0) + 1
            else:
                reserve_candidates.append(cand)

        # If active_candidates still has < DAILY_DROP_SIZE, top up from reserve_candidates
        while len(active_candidates) < DAILY_DROP_SIZE and reserve_candidates:
            active_candidates.append(reserve_candidates.pop(0))

        reserve_candidates = reserve_candidates[:RESERVE_DROP_SIZE]
        active_lesson_ids = [c["id"] for c in active_candidates]
        reserve_lesson_ids = [c["id"] for c in reserve_candidates]
        active_skill_names = []
        for c in active_candidates:
            sname = (skill_by_id.get(c.get("associated_skill_id")) or {}).get("name")
            if sname and sname not in active_skill_names:
                active_skill_names.append(sname)

        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "sprint_date": sprint_date,
            "target_skill_id": target_skill_id,
            "target_skill_name": target_skill_name,
            "focus_skill_names": active_skill_names or ([target_skill_name] if target_skill_name else []),
            "active_lesson_ids": active_lesson_ids,
            "reserve_lesson_ids": reserve_lesson_ids,
            "lesson_ids": active_lesson_ids,
            "passed_lesson_ids": [],
            "rerolls_used": rerolls_used,
            "is_completed": False,
            "created_at": _now_utc().isoformat(),
        }

    async def _hydrate_drop(self, drop: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Fetches full lesson details for the IDs in the daily drop using unified JSON + column hydration."""
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
                hydrated_item = hydrate_micro_content_row(
                    raw,
                    all_skills_map=all_skills_map,
                    fallback_skill_name=drop.get("target_skill_name") or "Core Skill",
                    passed_set=passed_set,
                )
                lessons.append(hydrated_item)

        streak_info = self.get_streak_info(user_id)
        now = _now_utc()
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        seconds_until_next = int((tomorrow - now).total_seconds())

        focus_names = drop.get("focus_skill_names") or []
        if not focus_names and lessons:
            for l in lessons:
                if l.get("skill_name") and l["skill_name"] not in focus_names:
                    focus_names.append(l["skill_name"])

        return {
            "id": drop.get("id"),
            "sprint_date": drop.get("sprint_date"),
            "target_skill_id": drop.get("target_skill_id"),
            "target_skill_name": drop.get("target_skill_name"),
            "focus_skill_names": focus_names,
            "lessons": lessons,
            "reserve_count": len(drop.get("reserve_lesson_ids", [])),
            "passed_count": len(drop.get("passed_lesson_ids", [])),
            "total_count": len(lessons),
            "is_completed": drop.get("is_completed", False),
            "rerolls_used": drop.get("rerolls_used", 0),
            "can_reroll": drop.get("rerolls_used", 0) < 1 and not drop.get("is_completed", False),
            "streak": streak_info,
            "seconds_until_next_drop": seconds_until_next,
        }

