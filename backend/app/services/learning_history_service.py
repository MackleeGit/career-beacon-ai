"""
Learning History Service:
Manages persistent learning history across three distinct dimensions:
  1. Assessment History (`assessment_attempts`):
     Every quiz attempt with answers, score, pass/fail, timestamp, and sequential attempt_number.
  2. Interaction & Activity (`user_content_activity`):
     Impressions, opening, completion, and repetition tracking for content deduplication.
  3. Resilient Persistence:
     Dual-layer persistence writing to Supabase tables when available, with automatic
     local durable file-backed persistence (in backend/data/) ensuring zero demo failures.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.database import supabase_client

logger = logging.getLogger("career_beacon.learning_history_service")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
ATTEMPTS_FILE = os.path.join(DATA_DIR, "assessment_attempts.json")
ACTIVITY_FILE = os.path.join(DATA_DIR, "user_content_activity.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearningHistoryService:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Assessment Attempt History
    # -------------------------------------------------------------------------

    def get_attempts_for_lesson(self, user_id: str, lesson_id: str) -> List[Dict[str, Any]]:
        """Retrieves all historical assessment attempts for a user on a given lesson."""
        attempts = []

        # 1. Try Supabase assessment_attempts
        try:
            res = supabase_client.table("assessment_attempts").select("*").eq(
                "user_id", user_id
            ).eq("lesson_id", lesson_id).order("attempt_number", desc=False).execute()
            if res.data:
                return res.data
        except Exception:
            pass

        # 2. Local durable store fallback
        try:
            if os.path.exists(ATTEMPTS_FILE):
                with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
                    all_attempts = json.load(f)
                    attempts = [
                        a for a in all_attempts
                        if a.get("user_id") == user_id and a.get("lesson_id") == lesson_id
                    ]
                    attempts.sort(key=lambda x: x.get("attempt_number", 1))
        except Exception as e:
            logger.warning(f"Failed to read local assessment attempts: {e}")

        return attempts

    def has_passed_lesson(self, user_id: str, lesson_id: str) -> bool:
        """Returns True if the learner has ever passed this lesson in any historical attempt."""
        # 1. Try Supabase
        try:
            res = supabase_client.table("assessment_attempts").select("id").eq(
                "user_id", user_id
            ).eq("lesson_id", lesson_id).eq("passed", True).limit(1).execute()
            if res.data and len(res.data) > 0:
                return True
        except Exception:
            pass

        # 2. Local fallback
        attempts = self.get_attempts_for_lesson(user_id, lesson_id)
        return any(a.get("passed") is True for a in attempts)

    def record_attempt(
        self,
        user_id: str,
        lesson_id: str,
        skill_id: Optional[str],
        answers: Dict[Any, str],
        score: int,
        total: int,
        percentage: float,
        passed: bool,
    ) -> Dict[str, Any]:
        """
        Durably records an assessment attempt with attempt sequence number.
        Retakes append a new attempt rather than overwriting historical records.
        """
        existing = self.get_attempts_for_lesson(user_id, lesson_id)
        attempt_number = len(existing) + 1

        record = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "skill_id": skill_id,
            "attempt_number": attempt_number,
            "answers": {str(k): str(v) for k, v in answers.items()},
            "score": score,
            "total": total,
            "percentage": percentage,
            "passed": passed,
            "created_at": _now_iso(),
        }

        # 1. Try remote Supabase table
        try:
            supabase_client.table("assessment_attempts").insert(record).execute()
        except Exception:
            pass

        # 2. Persist to local durable file
        try:
            all_attempts = []
            if os.path.exists(ATTEMPTS_FILE):
                try:
                    with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
                        all_attempts = json.load(f)
                except Exception:
                    all_attempts = []
            all_attempts.append(record)
            with open(ATTEMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_attempts, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist assessment attempt locally: {e}")

        return record

    # -------------------------------------------------------------------------
    # 2. User Content Activity & Interaction Tracking
    # -------------------------------------------------------------------------

    def get_user_activity_map(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Returns map of content_id -> activity details for the learner."""
        activity_map: Dict[str, Dict[str, Any]] = {}

        # 1. Try Supabase
        try:
            res = supabase_client.table("user_content_activity").select("*").eq(
                "user_id", user_id
            ).execute()
            if res.data:
                for row in res.data:
                    activity_map[row["content_id"]] = row
                return activity_map
        except Exception:
            pass

        # 2. Local fallback
        try:
            if os.path.exists(ACTIVITY_FILE):
                with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    all_act = json.load(f)
                    for row in all_act:
                        if row.get("user_id") == user_id:
                            activity_map[row["content_id"]] = row
        except Exception as e:
            logger.warning(f"Failed to read local content activity: {e}")

        return activity_map

    def record_impressions(self, user_id: str, content_ids: List[str]) -> None:
        """
        Records that learning resources were displayed in the learner's recommendation feed.
        Increments times_recommended and updates last_seen_at.
        """
        if not content_ids:
            return

        now = _now_iso()
        local_records = []
        if os.path.exists(ACTIVITY_FILE):
            try:
                with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    local_records = json.load(f)
            except Exception:
                local_records = []

        local_map = {(r["user_id"], r["content_id"]): r for r in local_records}

        for cid in content_ids:
            # Remote upsert attempt
            try:
                existing_res = supabase_client.table("user_content_activity").select(
                    "times_recommended"
                ).eq("user_id", user_id).eq("content_id", cid).execute()
                if existing_res.data:
                    current_times = existing_res.data[0].get("times_recommended", 1)
                    supabase_client.table("user_content_activity").update({
                        "times_recommended": current_times + 1,
                        "last_seen_at": now,
                    }).eq("user_id", user_id).eq("content_id", cid).execute()
                else:
                    supabase_client.table("user_content_activity").insert({
                        "user_id": user_id,
                        "content_id": cid,
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "times_recommended": 1,
                    }).execute()
            except Exception:
                pass

            # Local update
            key = (user_id, cid)
            if key in local_map:
                local_map[key]["times_recommended"] = local_map[key].get("times_recommended", 1) + 1
                local_map[key]["last_seen_at"] = now
            else:
                local_map[key] = {
                    "user_id": user_id,
                    "content_id": cid,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "opened_at": None,
                    "completed_at": None,
                    "times_recommended": 1,
                }

        try:
            with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(list(local_map.values()), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist impressions locally: {e}")

    def record_content_open(self, user_id: str, content_id: str) -> None:
        """Records when a learner opens a learning resource."""
        now = _now_iso()
        # Remote update / insert
        try:
            res = supabase_client.table("user_content_activity").select("times_recommended").eq(
                "user_id", user_id
            ).eq("content_id", content_id).execute()
            if res.data:
                supabase_client.table("user_content_activity").update({
                    "opened_at": now,
                    "last_seen_at": now,
                }).eq("user_id", user_id).eq("content_id", content_id).execute()
            else:
                supabase_client.table("user_content_activity").insert({
                    "user_id": user_id,
                    "content_id": content_id,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "opened_at": now,
                    "times_recommended": 1,
                }).execute()
        except Exception:
            pass

        # Local update / insert
        try:
            records = []
            if os.path.exists(ACTIVITY_FILE):
                try:
                    with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception:
                    records = []

            found = False
            for r in records:
                if r.get("user_id") == user_id and r.get("content_id") == content_id:
                    r["opened_at"] = now
                    r["last_seen_at"] = now
                    found = True
                    break
            if not found:
                records.append({
                    "user_id": user_id,
                    "content_id": content_id,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "opened_at": now,
                    "completed_at": None,
                    "times_recommended": 1,
                })
            with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record content open locally: {e}")

    def record_content_completion(self, user_id: str, content_id: str) -> None:
        """Records when a learner marks a learning resource complete."""
        now = _now_iso()
        # Remote update / insert
        try:
            res = supabase_client.table("user_content_activity").select("times_recommended").eq(
                "user_id", user_id
            ).eq("content_id", content_id).execute()
            if res.data:
                supabase_client.table("user_content_activity").update({
                    "completed_at": now,
                    "last_seen_at": now,
                }).eq("user_id", user_id).eq("content_id", content_id).execute()
            else:
                supabase_client.table("user_content_activity").insert({
                    "user_id": user_id,
                    "content_id": content_id,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "completed_at": now,
                    "times_recommended": 1,
                }).execute()
        except Exception:
            pass

        # Local update / insert
        try:
            records = []
            if os.path.exists(ACTIVITY_FILE):
                try:
                    with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception:
                    records = []

            found = False
            for r in records:
                if r.get("user_id") == user_id and r.get("content_id") == content_id:
                    r["completed_at"] = now
                    r["last_seen_at"] = now
                    found = True
                    break
            if not found:
                records.append({
                    "user_id": user_id,
                    "content_id": content_id,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "opened_at": None,
                    "completed_at": now,
                    "times_recommended": 1,
                })
            with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record content completion locally: {e}")
