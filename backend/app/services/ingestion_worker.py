"""
backend/app/services/ingestion_worker.py
----------------------------------------
Autonomous Content Ingestion & Reservoir Seeding Worker for Career Beacon.
Operates on the Offline Ingestion Plane:
1. Analyzes registered user enrollments and skill deficit gaps across canonical career tracks.
2. Prioritizes skills with low lesson counts (< 4 verified lessons in micro_content).
3. Polls authorized domain adapters (YouTube, MDN, Open Textbook, Europe PMC, arXiv, OWASP, etc.).
4. Enforces strict fail-closed pedagogical quality gates (dual vector cosine + centroid margin).
   Zero filler, zero synthetic mocks, zero ungrounded text.
5. Emits real-time telemetry for supervisor and administrator review.
"""

import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.core.database import supabase_client
from app.services.content_service import ContentService
from app.services.daily_drop_service import DailyDropService
from app.core.career_fields import classify_career_field, CAREER_FIELDS

logger = logging.getLogger("career_beacon.ingestion_worker")


class IngestionTelemetryCollector:
    """Collects timestamped execution telemetry for Admin UI streaming."""
    def __init__(self):
        self.logs: List[str] = []

    def emit(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.logs.append(entry)
        logger.info(entry)


class IngestionWorkerService:
    def __init__(self):
        self.content_service = ContentService()
        self.daily_drop_service = DailyDropService()

    async def get_enrolled_skills_priority(self) -> List[Dict[str, Any]]:
        """
        Scans registered user profiles and user_skills to identify all skills with active demand.
        Returns skills ranked by learner deficit count and low micro_content lesson coverage.
        """
        # 1. Fetch user skills
        try:
            res_uskills = supabase_client.table("user_skills").select("user_id, skill_id, proficiency").execute()
            uskills = res_uskills.data or []
        except Exception as e:
            logger.error(f"Error reading user_skills: {e}")
            uskills = []

        if not uskills:
            return []

        # 2. Group by skill_id
        skill_demand: Dict[str, Dict[str, Any]] = {}
        for row in uskills:
            sid = row.get("skill_id")
            if not sid:
                continue
            if sid not in skill_demand:
                skill_demand[sid] = {"enrolled_count": 0, "deficit_count": 0}
            skill_demand[sid]["enrolled_count"] += 1
            if (row.get("proficiency") or 0) <= 50:
                skill_demand[sid]["deficit_count"] += 1

        skill_ids = list(skill_demand.keys())
        if not skill_ids:
            return []

        # 3. Fetch skill names and categories
        res_skills = supabase_client.table("skills").select("id, name, category").in_("id", skill_ids).execute()
        skills_map = {s["id"]: s for s in (res_skills.data or [])}

        # 4. Count existing lessons in micro_content
        res_content = supabase_client.table("micro_content").select("associated_skill_id").in_("associated_skill_id", skill_ids).execute()
        lesson_counts: Dict[str, int] = {}
        for c in (res_content.data or []):
            asid = c.get("associated_skill_id")
            if asid:
                lesson_counts[asid] = lesson_counts.get(asid, 0) + 1

        # 5. Fetch associated career titles via profiles
        res_profiles = supabase_client.table("profiles").select("id, target_career_id").execute()
        user_to_career_id = {p["id"]: p.get("target_career_id") for p in (res_profiles.data or []) if p.get("target_career_id")}
        
        career_ids = list(set(user_to_career_id.values()))
        career_names_map = {}
        if career_ids:
            c_res = supabase_client.table("careers").select("id, title").in_("id", career_ids).execute()
            career_names_map = {c["id"]: c.get("title", "") for c in (c_res.data or [])}

        # Associate each skill with its most prominent career
        skill_to_career_name: Dict[str, str] = {}
        for row in uskills:
            sid = row.get("skill_id")
            uid = row.get("user_id")
            if sid and uid and sid not in skill_to_career_name:
                cid = user_to_career_id.get(uid)
                if cid and cid in career_names_map:
                    skill_to_career_name[sid] = career_names_map[cid]

        # 6. Cross-reference Commit Ledger so already-worked skills rotate to the back of the queue
        try:
            from app.services.ingestion_batch_service import ingestion_batch_service
            work_ledger = ingestion_batch_service.get_skill_work_ledger()
        except Exception:
            work_ledger = {}

        # 7. Assemble ranked priority list
        ranked: List[Dict[str, Any]] = []
        for sid, counts in skill_demand.items():
            sk_meta = skills_map.get(sid, {})
            sname_val = sk_meta.get("name", "Core Competency")
            current_lessons = lesson_counts.get(sid, 0)
            career_title = skill_to_career_name.get(sid, "Professional Practice")
            field_meta = classify_career_field(career_title)
            last_worked_at = work_ledger.get(sid) or work_ledger.get(sname_val.strip().lower()) or ""

            ranked.append({
                "skill_id": sid,
                "skill_name": sname_val,
                "category": sk_meta.get("category", "Core"),
                "career_title": career_title,
                "field_id": field_meta["field_id"],
                "field_label": field_meta["label"],
                "enrolled_count": counts["enrolled_count"],
                "deficit_count": counts["deficit_count"],
                "current_lesson_count": current_lessons,
                "needs_ingestion": current_lessons < 4,
                "has_commit": bool(last_worked_at),
                "last_worked_at": last_worked_at,
            })

        # Sort:
        #   1) needs_ingestion first
        #   2) untouched skills (has_commit=False) before already-worked skills
        #   3) least-recently-worked (last_worked_at ascending) so cycles rotate cleanly across skills
        #   4) lowest current lesson count, then highest deficit learner count
        ranked.sort(
            key=lambda x: (
                0 if x["needs_ingestion"] else 1,
                1 if x["has_commit"] else 0,
                x["last_worked_at"],
                x["current_lesson_count"],
                -x["deficit_count"],
            )
        )
        return ranked

    async def run_nightly_batch(
        self,
        max_skills: int = 5,
        target_lessons_per_skill: int = 3,
        force_all: bool = False,
        inter_attempt_delay_sec: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Executes the nightly autonomous ingestion sweep:
        1. Identifies deficit skills with low lesson counts.
        2. Ingests and synthesizes verified lessons across alternating video and written adapters.
        3. Strict quality filtering: fails closed on low substance.
        """
        telemetry = IngestionTelemetryCollector()
        telemetry.emit("Nightly Autonomous Content Ingestion Worker started.")

        priorities = await self.get_enrolled_skills_priority()
        if not priorities:
            telemetry.emit("No registered user skills found in database. Ingestion standby.")
            return {"status": "success", "seeded_count": 0, "logs": telemetry.logs}

        candidates = [p for p in priorities if p["needs_ingestion"] or force_all][:max_skills]
        telemetry.emit(f"Identified {len(candidates)} prioritized skills needing reservoir top-up (out of {len(priorities)} total enrolled skills).")

        seeded_lessons = []
        failed_count = 0

        for item in candidates:
            sid = item["skill_id"]
            sname = item["skill_name"]
            ctitle = item["career_title"]
            fid = item["field_id"]
            current_cnt = item["current_lesson_count"]
            deficit_cnt = item["deficit_count"]

            telemetry.emit(f"--- [SKILL] '{sname}' ({ctitle} | {item['field_label']}) ---")
            telemetry.emit(f"    Deficit Learners: {deficit_cnt} | Current Reservoir Count: {current_cnt} / {target_lessons_per_skill}")

            needed = max(1, target_lessons_per_skill - current_cnt)

            # Inspect existing titles in reservoir to prevent duplicate sub-topic generation
            existing_titles: List[str] = []
            try:
                ex_res = supabase_client.table("micro_content").select("title").eq("associated_skill_id", sid).execute()
                existing_titles = [r["title"] for r in (ex_res.data or []) if r.get("title")]
            except Exception:
                existing_titles = []

            if existing_titles:
                telemetry.emit(f"    Anti-Duplication Context: {len(existing_titles)} existing lesson(s) locked against overlap.")

            # LLM Curriculum Planner: 1 call to decompose skill into `needed` orthogonal sub-topics & site queries
            subtopic_plans = await self.content_service.plan_skill_curriculum_subtopics(
                skill_name=sname,
                career_title=ctitle,
                category=item.get("category", "Core"),
                needed_count=needed,
                existing_titles=existing_titles,
            )
            if subtopic_plans and subtopic_plans[0].get("planner_source") == "fallback":
                telemetry.emit(
                    f"    [WARNING] LLM Curriculum Planner FAILED ({subtopic_plans[0].get('fallback_reason', 'error')}) -> Using deterministic fallback for '{sname}'."
                )
            else:
                telemetry.emit(
                    f"    LLM Curriculum Planner: Decomposed '{sname}' into {len(subtopic_plans)} progressive, non-overlapping sub-topics."
                )

            skill_seeded_sources = []
            skill_seeded_ids = []

            for attempt_idx, plan_item in enumerate(subtopic_plans):
                pref_adapters = plan_item.get("preferred_adapters") or (
                    ["youtube"] if attempt_idx % 2 == 0 else ["mdn", "open_textbook", "clinical_science", "arxiv", "finance", "owasp"]
                )
                sub_focus = plan_item.get("subtopic_focus", sname)
                tax_query = plan_item.get("search_query", sname)
                t_diff = plan_item.get("target_difficulty", 2)

                telemetry.emit(
                    f"    Attempt {attempt_idx + 1}/{needed} [Tier {t_diff} | Sub-Topic: '{sub_focus}']:"
                )
                telemetry.emit(
                    f"      -> Taxonomy Query: '{tax_query}' | Target Adapters: {pref_adapters}"
                )

                try:
                    lesson = await self.content_service.generate_dynamic_lesson_for_skill(
                        skill_id=sid,
                        skill_name=sname,
                        category=item.get("category", "Core"),
                        career_title=ctitle,
                        target_proficiency=20,
                        preferred_adapters=pref_adapters,
                        subtopic_plan=plan_item,
                    )
                    if lesson and lesson.get("id"):
                        telemetry.emit(f"    SUCCESS: Ingested '{lesson.get('title')}' via {lesson.get('source_adapter')} ({lesson.get('source_name')})")
                        telemetry.emit(f"    Checkpoints: 5 Grounded MCQs + Pedagogical Regard & Anti-Duplication Gates passed (Difficulty: {lesson.get('difficulty_level', t_diff)}).")
                        seeded_lessons.append(lesson)
                        skill_seeded_ids.append(lesson["id"])
                        skill_seeded_sources.append({
                            "name": lesson.get("source_name", "Authoritative Source"),
                            "adapter": lesson.get("source_adapter", "web"),
                            "url": lesson.get("source_url", ""),
                            "trust_score": lesson.get("source_trust_score", 0.95),
                        })
                    else:
                        telemetry.emit(f"    REJECTED: Source failed LLM pedagogical regard rubric, vector threshold, or semantic deduplication gate.")
                        failed_count += 1
                except Exception as ex:
                    telemetry.emit(f"    NOTICE: Ingestion attempt exception: {ex}")
                    failed_count += 1

                if inter_attempt_delay_sec > 0:
                    await asyncio.sleep(inter_attempt_delay_sec)

            try:
                from app.services.ingestion_batch_service import ingestion_batch_service
                if skill_seeded_ids:
                    commit_rec = ingestion_batch_service.record_commit(
                        career_title=ctitle,
                        skill_name=sname,
                        sources=skill_seeded_sources,
                        lesson_ids=skill_seeded_ids,
                        message=f"Nightly Worker: Seeded {len(skill_seeded_ids)} non-overlapping sub-topic lesson(s) for {sname}",
                        author="Nightly Autonomous Worker",
                        status="approved",
                        skill_id=sid,
                    )
                    telemetry.emit(f"    Commit Ledger: Recorded batch #{commit_rec['commit_hash']} ({len(skill_seeded_ids)} lesson(s)).")
                else:
                    # Record rotation checkpoint so next scheduled cycle switches to the next skill instead of repeating
                    checkpoint_rec = ingestion_batch_service.record_commit(
                        career_title=ctitle,
                        skill_name=sname,
                        sources=[],
                        lesson_ids=[],
                        message=f"Rotation Checkpoint: Evaluated {sname} (0 new sources met strict gates; rotated to back of queue)",
                        author="Nightly Autonomous Worker",
                        status="pending",
                        skill_id=sid,
                    )
                    telemetry.emit(f"    Commit Ledger: Recorded rotation checkpoint #{checkpoint_rec['commit_hash']} to prevent repeat polling.")
            except Exception as batch_err:
                logger.debug(f"Batch commit ledger warning: {batch_err}")

        telemetry.emit(f"Nightly Batch Completed: {len(seeded_lessons)} verified lessons committed, {failed_count} rejected by quality gates.")
        return {
            "status": "success",
            "seeded_count": len(seeded_lessons),
            "rejected_count": failed_count,
            "lessons": seeded_lessons,
            "logs": telemetry.logs,
        }

    async def run_daily_drop_batch(self) -> Dict[str, Any]:
        """
        Executes the Daily Drop Personalization Worker for all registered learners:
        Pre-curates tomorrow's 5 primary + 5 reserve lessons from the pre-seeded reservoir.
        """
        telemetry = IngestionTelemetryCollector()
        telemetry.emit("Daily Drop Personalization Worker initialized.")

        try:
            res = supabase_client.table("profiles").select("id, full_name, email, target_career_id").execute()
            learners = [p for p in (res.data or []) if p.get("target_career_id")]
        except Exception as e:
            telemetry.emit(f"Error fetching enrolled learners: {e}")
            return {"status": "error", "logs": telemetry.logs}

        telemetry.emit(f"Discovered {len(learners)} enrolled learners with active target careers.")
        curated_drops = []

        for p in learners:
            uid = p["id"]
            user_label = p.get("full_name") or p.get("email") or uid[:8]
            telemetry.emit(f"Compiling Daily Drop for learner '{user_label}'...")

            try:
                # Runs the RRF + difficulty + history cooldown curation from pre-seeded micro_content
                drop = await self.daily_drop_service.trigger_daily_worker(user_id=uid, force_fresh=True)
                primary_cnt = len(drop.get("lessons", []))
                reserve_cnt = drop.get("reserve_count", 0)
                focus_skills = ", ".join(drop.get("focus_skill_names", []))

                telemetry.emit(f"    Completed: {primary_cnt} Primary + {reserve_cnt} Reserve lessons assembled.")
                telemetry.emit(f"    Focus Competencies: {focus_skills or 'Core Track'}")
                curated_drops.append({
                    "user_id": uid,
                    "user_name": user_label,
                    "primary_count": primary_cnt,
                    "reserve_count": reserve_cnt,
                    "focus_skills": drop.get("focus_skill_names", []),
                })
            except Exception as ex:
                telemetry.emit(f"    Personalization notice for {user_label}: {ex}")

        telemetry.emit(f"Daily Drop Worker Finished: {len(curated_drops)} active learner drops synchronized.")
        return {
            "status": "success",
            "curated_count": len(curated_drops),
            "drops": curated_drops,
            "logs": telemetry.logs,
        }


# Singleton worker instance
ingestion_worker_service = IngestionWorkerService()
