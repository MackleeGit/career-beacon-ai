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
import tempfile
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.database import supabase_client

logger = logging.getLogger("career_beacon.learning_history_service")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
ATTEMPTS_FILE = os.path.join(DATA_DIR, "assessment_attempts.json")
ACTIVITY_FILE = os.path.join(DATA_DIR, "user_content_activity.json")
_JSON_IO_LOCK = threading.RLock()


def _safe_load_json_list(path: str) -> List[Dict[str, Any]]:
    with _JSON_IO_LOCK:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed reading {path}: {e}")
            return []


def _safe_save_json_list(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _JSON_IO_LOCK:
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            os.replace(tmp_path, path)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            logger.warning(f"Failed saving {path}: {e}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearningHistoryService:
    _remote_table_available: Optional[bool] = None

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
        all_attempts = _safe_load_json_list(ATTEMPTS_FILE)
        attempts = [
            a for a in all_attempts
            if a.get("user_id") == user_id and a.get("lesson_id") == lesson_id
        ]
        attempts.sort(key=lambda x: x.get("attempt_number", 1))
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
        all_attempts = _safe_load_json_list(ATTEMPTS_FILE)
        all_attempts.append(record)
        _safe_save_json_list(ATTEMPTS_FILE, all_attempts)

        return record

    # -------------------------------------------------------------------------
    # 2. User Content Activity & Interaction Tracking
    # -------------------------------------------------------------------------

    def get_user_activity_map(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Returns map of content_id -> activity details for the learner."""
        activity_map: Dict[str, Dict[str, Any]] = {}

        # 1. Try Supabase if table is known to be available
        if LearningHistoryService._remote_table_available is not False:
            try:
                res = supabase_client.table("user_content_activity").select("*").eq(
                    "user_id", user_id
                ).execute()
                LearningHistoryService._remote_table_available = True
                if res.data:
                    for row in res.data:
                        activity_map[row["content_id"]] = row
                    return activity_map
            except Exception as e:
                if "PGRST205" in str(e) or "Could not find the table" in str(e):
                    LearningHistoryService._remote_table_available = False
                logger.debug(f"Remote user_content_activity unavailable: {e}")

        # 2. Local fallback
        all_act = _safe_load_json_list(ACTIVITY_FILE)
        for row in all_act:
            if row.get("user_id") == user_id:
                activity_map[row["content_id"]] = row

        return activity_map

    def record_impressions(self, user_id: str, content_ids: List[str]) -> None:
        """
        Records that learning resources were displayed in the learner's recommendation feed.
        Increments times_recommended and updates last_seen_at.
        """
        if not content_ids:
            return

        now = _now_iso()
        local_records = _safe_load_json_list(ACTIVITY_FILE)
        local_map = {(r["user_id"], r["content_id"]): r for r in local_records}

        for cid in content_ids:
            # Remote upsert attempt if table exists
            if LearningHistoryService._remote_table_available is not False:
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
                    LearningHistoryService._remote_table_available = True
                except Exception as e:
                    if "PGRST205" in str(e) or "Could not find the table" in str(e):
                        LearningHistoryService._remote_table_available = False

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

        _safe_save_json_list(ACTIVITY_FILE, list(local_map.values()))

    def record_content_open(self, user_id: str, content_id: str) -> None:
        """Records when a learner opens a learning resource."""
        now = _now_iso()
        # Remote update / insert
        if LearningHistoryService._remote_table_available is not False:
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
                LearningHistoryService._remote_table_available = True
            except Exception as e:
                if "PGRST205" in str(e) or "Could not find the table" in str(e):
                    LearningHistoryService._remote_table_available = False

        # Local update / insert
        records = _safe_load_json_list(ACTIVITY_FILE)
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
        _safe_save_json_list(ACTIVITY_FILE, records)

    def record_content_completion(self, user_id: str, content_id: str) -> None:
        """Records when a learner marks a learning resource complete."""
        now = _now_iso()
        # Remote update / insert
        if LearningHistoryService._remote_table_available is not False:
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
                LearningHistoryService._remote_table_available = True
            except Exception as e:
                if "PGRST205" in str(e) or "Could not find the table" in str(e):
                    LearningHistoryService._remote_table_available = False

        # Local update / insert
        records = _safe_load_json_list(ACTIVITY_FILE)
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
        _safe_save_json_list(ACTIVITY_FILE, records)
