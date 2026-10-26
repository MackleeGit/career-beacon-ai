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
    - Growth in Breadth vs. Weight: Boosts neglected peripheral skills in the career graph.
    - Source Trust Scoring: Multiplies by organic source trust modifier (0.00 - 1.00).
    - Sorts and delivers final Top 5 micro-learning feed.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Dict, Any, List, Optional
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.content_service import ContentService
from app.services.learning_history_service import LearningHistoryService, ATTEMPTS_FILE, ACTIVITY_FILE

logger = logging.getLogger("career_beacon.recommendation_service")


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


class RecommendationService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.content_service = ContentService()
        self.history_service = LearningHistoryService()

    async def get_recommendations_for_user(
        self,
        user_id: str,
        limit: int = 5,
        offset: int = 0,
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
        career_res = supabase_client.table("careers").select("id, title, description").eq("id", career_id).execute()
        career_title = career_res.data[0]["title"] if career_res.data else "General Tech"

        # 2. Fetch user's enrolled skills and current proficiencies (Skill Graph Coordinates)
        user_skills_res = supabase_client.table("user_skills").select(
            "skill_id, proficiency, skills(id, name, category)"
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
                    "proficiency": prof,
                })
                skill_proficiency_map[s_id] = prof
                skill_name_map[s_id] = sk["name"]

        # If user has no skills mapped yet, return empty
        if not user_skills:
            logger.info(f"User {user_id} has no skills tracked in user_skills.")
            return []

        # 2B. Fetch Career Graph Metadata (Importance, Tiers, and Ranks)
        career_skills_map: Dict[str, Dict[str, Any]] = {}
        try:
            cs_res = supabase_client.table("career_skills").select(
                "skill_id, importance, importance_score, tier, rank"
            ).eq("career_id", career_id).execute()
            for row in (cs_res.data or []):
                career_skills_map[row["skill_id"]] = row
        except Exception as e:
            logger.warning(f"Failed to fetch career_skills metadata for career {career_id}: {e}")

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

        # 3. Construct Skill-Gap Frontier Query
        # Sort skills by proficiency ascending (biggest gap first)
        sorted_by_gap = sorted(user_skills, key=lambda s: s["proficiency"])
        priority_skills = sorted_by_gap[:4]
        gap_skill_names = ", ".join(s["name"] for s in priority_skills)
        frontier_query_text = (
            f"Target Career: {career_title}. "
            f"Priority micro-learning skills to improve: {gap_skill_names}."
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
                    "match_count": 30,
                }
            ).execute()
            if rpc_res.data:
                candidates = rpc_res.data
                logger.info(f"Stage 1 Coarse Filter retrieved {len(candidates)} candidates via match_micro_content RPC.")
        except Exception as e:
            logger.warning(f"match_micro_content RPC call failed ({e}); falling back to relational fetch.")

        # Fallback: Relational candidate fetch targeting ONLY the learner's relevant career skills (NO arbitrary limit(30))
        if not candidates and user_skill_ids:
            try:
                table_res = supabase_client.table("micro_content").select("*").in_(
                    "associated_skill_id", list(user_skill_ids)
                ).limit(30).execute()
                candidates = table_res.data or []
                # Association identifies fallback scope, not semantic relevance. Score
                # each result from its stored vector; omit lessons with no usable vector.
                for c in candidates:
                    if c.get("similarity") is None:
                        c["similarity"] = _cosine_similarity(query_embedding, c.get("embedding"))
                candidates = [c for c in candidates if c.get("similarity") is not None and c["similarity"] >= 0.25]
                logger.info(f"Stage 1 Relational Fallback retrieved {len(candidates)} targeted candidates for user skills.")
            except Exception as e:
                logger.error(f"Failed to fetch targeted candidate micro-content: {e}")
                candidates = []

        if not candidates:
            candidates = []

        # 4B. JUST-IN-TIME DYNAMIC CURRICULUM POPULATION
        # Verify how many candidate lessons actually match the learner's enrolled career skills
        relevant_candidates = [
            c for c in candidates
            if c.get("associated_skill_id") in user_skill_ids
        ]

        # If database lacks sufficient domain content for this career (< limit relevant lessons):
        if len(relevant_candidates) < limit:
            needed_count = limit - len(relevant_candidates)
            logger.info(
                f"Learner {user_id} ({career_title}) has {len(relevant_candidates)}/{limit} relevant lessons in DB. "
                f"Triggering Just-In-Time dynamic curriculum generation for {needed_count} skills..."
            )
            skills_with_content = set(c.get("associated_skill_id") for c in relevant_candidates if c.get("associated_skill_id"))
            skills_needing_content = [s for s in priority_skills if s["id"] not in skills_with_content]

            if not skills_needing_content:
                skills_needing_content = [s for s in user_skills if s["id"] not in skills_with_content][:needed_count]

            if skills_needing_content:
                sem = asyncio.Semaphore(2)

                async def _paced_gen(s):
                    async with sem:
                        res = await self.content_service.generate_dynamic_lesson_for_skill(
                            skill_id=s["id"],
                            skill_name=s["name"],
                            category=s.get("category", "Core"),
                            career_title=career_title,
                            target_proficiency=s["proficiency"],
                        )
                        await asyncio.sleep(0.2)
                        return res

                tasks = [_paced_gen(s) for s in skills_needing_content[:needed_count]]
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

        if not candidates:
            return []

        # Build skill details lookup for all skills in DB
        all_skills_res = supabase_client.table("skills").select("id, name, category").execute()
        all_skills_map = {s["id"]: s for s in (all_skills_res.data or [])}

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
            elif completed and not has_passed_this_lesson:
                # Completed reading but failed quiz: seek alternative resource or revisit
                activity_multiplier = 0.70
            elif times_rec >= 3 and not opened:
                # Repeatedly recommended without learner engagement: demote to avoid stale feed spam
                activity_multiplier = 0.60
            elif times_rec >= 1 and not opened and not is_recent_session_impression:
                # Shown previously in a past session but never opened: slight deprioritization
                activity_multiplier = 0.90
            else:
                # Fresh / unseen content, or active in-session pagination
                activity_multiplier = 1.00

            # Composite Re-Rank Score:
            # Preserves base_sim (semantic relevance) as a primary multiplier.
            final_score = (
                base_sim
                * diff_multiplier
                * gap_multiplier
                * prereq_penalty
                * unblocking_boost
                * career_importance_multiplier
                * activity_multiplier
            )

            # Enrich item for frontend presentation
            skill_info = all_skills_map.get(assoc_skill_id, {})
            skill_name = skill_info.get("name") or "Core Skill"
            skill_category = skill_info.get("category") or "Technical"

            # Parse quizzes and summary bullets safely
            quizzes_data = item.get("quizzes")
            summary_bullets = item.get("summary_bullets") or item.get("summary") or ""
            
            # Check content JSON if fields are missing
            if (not quizzes_data or not summary_bullets) and item.get("content"):
                import json
                try:
                    c_data = item.get("content")
                    if isinstance(c_data, str):
                        c_data = json.loads(c_data)
                    if isinstance(c_data, dict):
                        if not quizzes_data:
                            quizzes_data = c_data.get("quizzes")
                        if not summary_bullets:
                            summary_bullets = c_data.get("summary_bullets") or c_data.get("summary") or ""
                except Exception:
                    pass

            if isinstance(quizzes_data, str):
                import json
                try:
                    quizzes_data = json.loads(quizzes_data)
                except Exception:
                    quizzes_data = []

            ranked_items.append({
                "id": item["id"],
                "title": item["title"],
                "source_url": item.get("source_url", ""),
                "summary_bullets": summary_bullets,
                "difficulty_level": item_diff,
                "source_trust_score": trust_score,
                "quizzes": quizzes_data or [],
                "associated_skill_id": assoc_skill_id,
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
                "relevance_score": round(final_score, 4),
            })

        # Sort descending by enrolled skill alignment first, then composite re-ranked score
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

        final_feed = ranked_items[offset : offset + limit]

        # Record feed impressions for delivered items
        delivered_ids = [it["id"] for it in final_feed]
        self.history_service.record_impressions(user_id, delivered_ids)

        return final_feed

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

                if passed and not already_passed:
                    proficiency_increment = 10
                    new_proficiency = min(100, current_prof + 10)
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
            "feedback": detailed_feedback,
        }
