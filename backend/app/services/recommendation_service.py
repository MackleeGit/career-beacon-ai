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

import logging
from typing import Dict, Any, List, Optional
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("career_beacon.recommendation_service")


class RecommendationService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def get_recommendations_for_user(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
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

        # 4. STAGE 1: DATABASE COARSE FILTER (Top 30 Candidates via pgvector)
        candidates: List[Dict[str, Any]] = []
        try:
            rpc_res = supabase_client.rpc(
                "match_micro_content",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.0,
                    "match_count": 30,
                }
            ).execute()
            if rpc_res.data:
                candidates = rpc_res.data
                logger.info(f"Stage 1 Coarse Filter retrieved {len(candidates)} candidates via match_micro_content RPC.")
        except Exception as e:
            logger.warning(f"match_micro_content RPC call failed ({e}); falling back to relational fetch.")

        # Fallback if RPC failed or returned 0 rows
        if not candidates:
            try:
                table_res = supabase_client.table("micro_content").select("*").limit(30).execute()
                candidates = table_res.data or []
                logger.info(f"Stage 1 Fallback retrieved {len(candidates)} candidates from micro_content table.")
            except Exception as e:
                logger.error(f"Failed to fetch candidate micro-content: {e}")
                return []

        if not candidates:
            return []

        # Build skill details lookup for all skills in DB
        all_skills_res = supabase_client.table("skills").select("id, name, category").execute()
        all_skills_map = {s["id"]: s for s in (all_skills_res.data or [])}

        # 5. STAGE 2: PYTHON GRAPH RE-RANKER
        ranked_items = []
        for item in candidates:
            base_sim = float(item.get("similarity") or 0.65)
            # Bound base similarity between 0.1 and 1.0
            base_sim = max(0.1, min(1.0, base_sim))

            assoc_skill_id = item.get("associated_skill_id")
            user_prof = skill_proficiency_map.get(assoc_skill_id, 20)

            # A. Priority in Difficulty (Cognitive Load Gating)
            # Target difficulty tiers: 20% -> Diff 1-2 | 50% -> Diff 2-3 | 80% -> Diff 3-4 | 100% -> Diff 4-5
            item_diff = int(item.get("difficulty_level") or 2)
            expected_diff = max(1, min(5, round(user_prof / 22.0) + 1))

            if item_diff > (expected_diff + 1):
                # Harsh penalty for prematurely exposing learner to advanced content
                diff_multiplier = max(0.40, 1.0 - 0.25 * (item_diff - expected_diff))
            elif item_diff <= expected_diff:
                # Slight accessible reward
                diff_multiplier = 1.08
            else:
                diff_multiplier = 1.00

            # B. Growth in Breadth vs. Weight (Skill Gap Prioritization)
            # Skills with larger deficits (e.g. 20% proficiency) get a boost over already mastered skills
            gap_ratio = (100 - user_prof) / 100.0
            breadth_multiplier = 1.0 + (0.35 * gap_ratio)

            # C. Verification and Organic Source Trust Scoring
            trust_score = float(item.get("source_trust_score") or 0.85)
            trust_multiplier = max(0.2, min(1.0, trust_score))

            # Composite Re-Rank Score
            final_score = base_sim * diff_multiplier * breadth_multiplier * trust_multiplier

            # Enrich item for frontend presentation
            skill_info = all_skills_map.get(assoc_skill_id, {})
            skill_name = skill_info.get("name") or "Core Skill"
            skill_category = skill_info.get("category") or "Technical"

            # Parse quizzes safely if stored as JSON string
            quizzes_data = item.get("quizzes")
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
                "summary_bullets": item.get("summary_bullets", ""),
                "difficulty_level": item_diff,
                "source_trust_score": trust_score,
                "quizzes": quizzes_data or [],
                "associated_skill_id": assoc_skill_id,
                "skill_name": skill_name,
                "skill_category": skill_category,
                "user_current_proficiency": user_prof,
                "relevance_score": round(final_score, 4),
            })

        # Sort descending by re-ranked score
        ranked_items.sort(key=lambda x: x["relevance_score"], reverse=True)

        return ranked_items[:limit]

    async def submit_quiz_answer(
        self,
        user_id: str,
        lesson_id: str,
        answers: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        Evaluates a submitted quiz, provides instant feedback, and updates
        user_skills proficiency (+10% on pass) and marks 'Mastered' at 100%.
        """
        # Fetch lesson details
        lesson_res = supabase_client.table("micro_content").select("*").eq("id", lesson_id).execute()
        if not lesson_res.data:
            return {"error": "Lesson not found"}

        lesson = lesson_res.data[0]
        quizzes = lesson.get("quizzes", [])
        if isinstance(quizzes, str):
            import json
            try:
                quizzes = json.loads(quizzes)
            except Exception:
                quizzes = []

        total_questions = len(quizzes)
        if total_questions == 0:
            return {"error": "This lesson does not have an active quiz."}

        # Evaluate each question
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

        # Proficiency update logic (+10% if passed)
        skill_id = lesson.get("associated_skill_id")
        new_proficiency = None
        skill_mastered = False

        if skill_id:
            user_skill_res = supabase_client.table("user_skills").select("*").eq(
                "user_id", user_id
            ).eq("skill_id", skill_id).execute()

            if user_skill_res.data:
                current_prof = int(user_skill_res.data[0].get("proficiency", 20))
                if passed:
                    new_proficiency = min(100, current_prof + 10)
                else:
                    new_proficiency = current_prof

                skill_mastered = (new_proficiency >= 100)

                # Update DB
                supabase_client.table("user_skills").update({
                    "proficiency": new_proficiency,
                }).eq("user_id", user_id).eq("skill_id", skill_id).execute()

        # Repeated failure guidance ("Ask MENTOR" trigger)
        ask_mentor_suggested = not passed

        return {
            "passed": passed,
            "score": correct_count,
            "total": total_questions,
            "percentage": percentage,
            "proficiency_increment": 10 if passed else 0,
            "new_proficiency": new_proficiency,
            "skill_mastered": skill_mastered,
            "ask_mentor_suggested": ask_mentor_suggested,
            "feedback": detailed_feedback,
        }
