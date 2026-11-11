"""
backend/app/services/ingestion_batch_service.py
------------------------------------------------
Git-Commit Style Ingestion Ledger Service:
Maintains audit trail of all ingestion instances (commits):
- Commit Hash (7-char hex)
- Source adapters, URLs, and trust scores
- Associated skill and career targets
- Status governance: Approved / Pending / Disapproved (Rejected)
- Lesson-level editing (title, overview, quizzes, skill alignment)
Dual-layer persistence: Supabase + durable local fallback.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.database import supabase_client

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
BATCHES_FILE = os.path.join(DATA_DIR, "ingestion_batches.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_commit_hash(seed: str) -> str:
    h = hashlib.sha256(f"{seed}-{uuid.uuid4().hex}".encode("utf-8")).hexdigest()
    return h[:7]


class IngestionBatchService:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._ensure_seed_batches()

    def _ensure_seed_batches(self):
        if not os.path.exists(BATCHES_FILE):
            # Generate initial commits for seeded content
            initial_commits = [
                {
                    "id": "commit-a91df42",
                    "commit_hash": "a91df42",
                    "message": "Curriculum Seed: Full-Stack Engineer State & Database Architecture",
                    "career_title": "Full-Stack Engineer",
                    "skill_name": "React.js State Architecture",
                    "status": "approved",
                    "author": "Curriculum Engineering Team",
                    "created_at": "2026-11-11T03:00:00Z",
                    "sources": [
                        {
                            "name": "React Architecture Team / YouTube",
                            "adapter": "youtube",
                            "url": "https://www.youtube.com/watch?v=0ZJgIjIuY7U",
                            "trust_score": 0.95
                        },
                        {
                            "name": "PostgreSQL Global Development Group",
                            "adapter": "structured_tutorial",
                            "url": "https://www.postgresql.org/docs/current/indexes.html",
                            "trust_score": 0.95
                        },
                        {
                            "name": "Docker Documentation / CNCF",
                            "adapter": "structured_tutorial",
                            "url": "https://docs.docker.com/build/building/multi-stage/",
                            "trust_score": 0.95
                        }
                    ],
                    "lesson_count": 3,
                    "quiz_count": 15,
                    "summary": "Verified modules for React 18 Concurrent Mode, PostgreSQL indexing internals, and Docker multi-stage builds."
                },
                {
                    "id": "commit-b72e105",
                    "commit_hash": "b72e105",
                    "message": "Curriculum Seed: Registered Nurse Clinical Pharmacology & ESI Triage",
                    "career_title": "Registered Nurse",
                    "skill_name": "NCLEX Pharmacology & Dosage Calculations",
                    "status": "approved",
                    "author": "Clinical Review Board",
                    "created_at": "2026-11-11T03:15:00Z",
                    "sources": [
                        {
                            "name": "RegisteredNurseRN / NCLEX Review",
                            "adapter": "youtube",
                            "url": "https://www.youtube.com/watch?v=0kF6z8lR0pY",
                            "trust_score": 0.95
                        },
                        {
                            "name": "Agency for Healthcare Research and Quality (AHRQ)",
                            "adapter": "clinical_science",
                            "url": "https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html",
                            "trust_score": 0.95
                        },
                        {
                            "name": "Centers for Disease Control and Prevention (CDC)",
                            "adapter": "clinical_science",
                            "url": "https://www.cdc.gov/infection-control/hcp/isolation-precautions/",
                            "trust_score": 0.95
                        }
                    ],
                    "lesson_count": 3,
                    "quiz_count": 15,
                    "summary": "NCLEX drug dosages, Digoxin/Heparin therapeutic monitoring, ESI 5-level acuity triage, and CDC isolation procedures."
                },
                {
                    "id": "commit-c83fa99",
                    "commit_hash": "c83fa99",
                    "message": "Curriculum Seed: Data Science & Corporate Finance Standards",
                    "career_title": "Data Scientist",
                    "skill_name": "Machine Learning Pipeline Engineering",
                    "status": "approved",
                    "author": "Quantitative Standards Group",
                    "created_at": "2026-11-11T03:30:00Z",
                    "sources": [
                        {
                            "name": "Scikit-Learn Core Contributors",
                            "adapter": "structured_tutorial",
                            "url": "https://scikit-learn.org/stable/modules/compose.html",
                            "trust_score": 0.95
                        },
                        {
                            "name": "Corporate Finance Institute (CFI)",
                            "adapter": "finance",
                            "url": "https://corporatefinanceinstitute.com/resources/valuation/dcf-formula-guide/",
                            "trust_score": 0.95
                        }
                    ],
                    "lesson_count": 2,
                    "quiz_count": 10,
                    "summary": "Scikit-learn ColumnTransformer leakage prevention and corporate DCF valuation modeling."
                },
                {
                    "id": "commit-d94bb21",
                    "commit_hash": "d94bb21",
                    "message": "Curriculum Seed: Civil Infrastructure & Mathematical Optimization",
                    "career_title": "Civil Engineer",
                    "skill_name": "Structural Load & Beam Analysis",
                    "status": "approved",
                    "author": "Engineering Accreditation Committee",
                    "created_at": "2026-11-11T03:45:00Z",
                    "sources": [
                        {
                            "name": "OpenStax / ASCE",
                            "adapter": "open_textbook",
                            "url": "https://openstax.org/details/books/university-physics-volume-1",
                            "trust_score": 0.95
                        },
                        {
                            "name": "INFORMS / SciPy Optimization",
                            "adapter": "structured_tutorial",
                            "url": "https://scipy-lectures.org/advanced/optimizing/",
                            "trust_score": 0.95
                        }
                    ],
                    "lesson_count": 2,
                    "quiz_count": 10,
                    "summary": "Shear force / bending moment structural analysis and Simplex LP duality optimization."
                }
            ]
            self._save_batches(initial_commits)

    def _load_batches(self) -> List[Dict[str, Any]]:
        try:
            if os.path.exists(BATCHES_FILE):
                with open(BATCHES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ingestion-batch] Error loading local batches: {e}")
        return []

    def _save_batches(self, batches: List[Dict[str, Any]]) -> None:
        try:
            with open(BATCHES_FILE, "w", encoding="utf-8") as f:
                json.dump(batches, f, indent=2)
        except Exception as e:
            print(f"[ingestion-batch] Error saving local batches: {e}")

    def list_batches(self) -> List[Dict[str, Any]]:
        return self._load_batches()

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        batches = self._load_batches()
        for b in batches:
            if b.get("id") == batch_id or b.get("commit_hash") == batch_id:
                return b
        return None

    def record_commit(
        self,
        career_title: str,
        skill_name: str,
        sources: List[Dict[str, Any]],
        lesson_ids: List[str],
        message: Optional[str] = None,
        author: str = "Admin / Ingestion Worker",
        status: str = "approved",
    ) -> Dict[str, Any]:
        """Creates a new git-commit style record for an ingestion sweep or live probe."""
        commit_hash = _generate_commit_hash(f"{career_title}-{skill_name}")
        batch_id = f"commit-{commit_hash}"
        commit_msg = message or f"Ingested {len(lesson_ids)} lesson(s) for {career_title} ({skill_name})"

        record = {
            "id": batch_id,
            "commit_hash": commit_hash,
            "message": commit_msg,
            "career_title": career_title,
            "skill_name": skill_name,
            "status": status,
            "author": author,
            "created_at": _utc_now_iso(),
            "sources": sources,
            "lesson_ids": lesson_ids,
            "lesson_count": len(lesson_ids),
            "quiz_count": len(lesson_ids) * 5,
            "summary": f"Autonomous ingestion sweep targeting {skill_name} across {len(sources)} verified sources."
        }

        batches = self._load_batches()
        batches.insert(0, record)
        self._save_batches(batches)
        return record

    def set_batch_status(self, batch_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Approve or reject an entire ingestion batch."""
        if new_status not in ("approved", "rejected", "pending"):
            raise ValueError("Status must be approved, rejected, or pending")

        batches = self._load_batches()
        target_batch = None
        for b in batches:
            if b.get("id") == batch_id or b.get("commit_hash") == batch_id:
                b["status"] = new_status
                b["updated_at"] = _utc_now_iso()
                target_batch = b
                break

        if target_batch:
            self._save_batches(batches)

            # Cascade review_status to all associated lessons in micro_content
            lesson_ids = target_batch.get("lesson_ids", [])
            for lid in lesson_ids:
                try:
                    res = supabase_client.table("micro_content").select("content").eq("id", lid).execute()
                    if res.data:
                        raw_c = res.data[0].get("content")
                        c_dict = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                        c_dict["review_status"] = new_status
                        supabase_client.table("micro_content").update({
                            "content": json.dumps(c_dict)
                        }).eq("id", lid).execute()
                except Exception as cascade_err:
                    print(f"[ingestion-batch] Cascade error on lesson {lid}: {cascade_err}")

        return target_batch

    def edit_lesson(
        self,
        lesson_id: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        concept_overview: Optional[str] = None,
        practice_scenario: Optional[str] = None,
        difficulty_level: Optional[int] = None,
        quizzes: Optional[List[Dict[str, Any]]] = None,
        associated_skill_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Allows administrator to edit an ingested lesson, its questions, or its skill link."""
        res = supabase_client.table("micro_content").select("*").eq("id", lesson_id).execute()
        if not res.data:
            raise ValueError(f"Lesson '{lesson_id}' not found in Supabase micro_content")

        row = res.data[0]
        raw_c = row.get("content")
        c_dict = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})

        update_fields: Dict[str, Any] = {"updated_at": _utc_now_iso()}

        if title is not None and title.strip():
            update_fields["title"] = title.strip()
            c_dict["title"] = title.strip()

        if summary is not None:
            update_fields["summary"] = summary.strip()
            c_dict["summary"] = summary.strip()

        if concept_overview is not None:
            c_dict["concept_overview"] = concept_overview.strip()

        if practice_scenario is not None:
            c_dict["practice_scenario"] = practice_scenario.strip()

        if difficulty_level is not None:
            update_fields["difficulty_level"] = int(difficulty_level)
            c_dict["difficulty_level"] = int(difficulty_level)

        if quizzes is not None:
            update_fields["quizzes"] = quizzes
            c_dict["quizzes"] = quizzes

        if associated_skill_id is not None:
            update_fields["associated_skill_id"] = associated_skill_id
            c_dict["associated_skill_id"] = associated_skill_id

        update_fields["content"] = json.dumps(c_dict)

        supabase_client.table("micro_content").update(update_fields).eq("id", lesson_id).execute()
        return {
            "status": "success",
            "lesson_id": lesson_id,
            "message": "Lesson content and checkpoint questions successfully updated.",
            "updated_fields": list(update_fields.keys()),
        }


ingestion_batch_service = IngestionBatchService()

