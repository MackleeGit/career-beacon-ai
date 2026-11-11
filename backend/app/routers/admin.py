"""
backend/app/routers/admin.py

Academic & System Administration Router (Reload Triggered):
Provides clean operational endpoints for the Career Beacon Admin Command Center:
1. KPI System Health & Activity Metrics.
2. Career Taxonomy Governance (Review and approve AI-induced unreviewed careers).
3. Safety & Content Moderation (Flagged DMs, reported Q&As, and community posts).
4. Mentor Credential Verification (Toggle Gold Verified Mentor badge).
"""

from typing import List, Optional, Dict, Any
import os
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.database import supabase_client
from app.services.mentorship_service import mentorship_service
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_batch_service import ingestion_batch_service
from app.middleware.auth_middleware import get_verified_user_id

router = APIRouter(prefix="/api/admin", tags=["Admin"])
embedding_service = EmbeddingService()


class CareerReviewActionPayload(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    custom_title: Optional[str] = None
    custom_skills: Optional[List[str]] = None


class MentorVerifyPayload(BaseModel):
    verified: bool


class ModerationActionPayload(BaseModel):
    action: str = Field(..., pattern="^(dismiss|delete)$")
    item_id: str
    item_type: str = Field(..., pattern="^(message|pulse_post|question|answer)$")


# ---------------------------------------------------------------------------
# Helper: Check Admin Authorization
# ---------------------------------------------------------------------------
def require_admin_role(http_req: Request) -> str:
    user_id = get_verified_user_id(http_req)
    try:
        res = (
            supabase_client.table("profiles")
            .select("id, role, email")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if res.data:
            role = res.data[0].get("role")
            email = (res.data[0].get("email") or "").lower()
            if role == "admin" or email.startswith("admin@") or "admin" in email:
                return user_id
    except HTTPException:
        raise
    except Exception as e:
        print(f"[admin-auth] Error checking admin role: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify administrative authorization.")

    raise HTTPException(
        status_code=403,
        detail="Forbidden: Administrative privileges required to access this resource.",
    )


# ---------------------------------------------------------------------------
# 1. System Stats & Activity Metrics
# ---------------------------------------------------------------------------
@router.get("/stats")
async def get_system_stats(http_req: Request):
    require_admin_role(http_req)
    try:
        # 1. Total profiles by role
        prof_res = supabase_client.table("profiles").select("id, role").execute()
        profiles = prof_res.data or []
        learner_count = sum(1 for p in profiles if p.get("role") == "learner")
        mentor_count = sum(1 for p in profiles if p.get("role") == "mentor")
        total_users = len(profiles)

        # 2. Total careers & unreviewed careers
        careers_res = supabase_client.table("careers").select("id, review_status").execute()
        all_careers = careers_res.data or []
        total_careers = len(all_careers)
        unreviewed_careers = sum(1 for c in all_careers if c.get("review_status") == "unreviewed")

        # 3. Active mentorship service store metrics
        store = mentorship_service._ensure_store()
        mentors_registered = len(store.get("mentors", []))
        total_sessions = len(store.get("sessions", []))
        completed_sessions = sum(1 for s in store.get("sessions", []) if s.get("status") == "completed")
        active_connections = sum(1 for c in store.get("connections", []) if c.get("status") == "accepted")
        total_questions = len(store.get("questions", []))
        answered_questions = sum(1 for q in store.get("questions", []) if q.get("status") == "answered")
        total_pulse_posts = len(store.get("pulse_posts", []))

        return {
            "status": "success",
            "stats": {
                "total_users": total_users,
                "learner_count": learner_count,
                "mentor_count": max(mentor_count, mentors_registered),
                "total_careers": total_careers,
                "unreviewed_careers": unreviewed_careers,
                "active_connections": active_connections,
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "total_questions": total_questions,
                "answered_questions": answered_questions,
                "total_pulse_posts": total_pulse_posts,
            },
        }
    except Exception as e:
        print(f"[admin-stats] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch admin stats: {e}")


# ---------------------------------------------------------------------------
# 2. Career Taxonomy Governance (Review Organic / Induced Careers)
# ---------------------------------------------------------------------------
@router.get("/careers/pending")
async def get_pending_careers(http_req: Request):
    require_admin_role(http_req)
    try:
        res = (
            supabase_client.table("careers")
            .select("id, title, description, created_at, source_origin, review_status")
            .eq("review_status", "unreviewed")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        careers = res.data or []

        # Attach skills for each pending career
        results = []
        for c in careers:
            cid = c["id"]
            sk_res = (
                supabase_client.table("career_skills")
                .select("importance, skills(id, name, category)")
                .eq("career_id", cid)
                .execute()
            )
            skills = []
            for row in sk_res.data or []:
                s_obj = row.get("skills")
                if s_obj:
                    skills.append({
                        "id": s_obj.get("id"),
                        "name": s_obj.get("name"),
                        "category": s_obj.get("category"),
                        "importance": row.get("importance"),
                    })

            results.append({
                **c,
                "skills": skills,
            })

        return {"pending_careers": results, "count": len(results)}
    except Exception as e:
        print(f"[admin-pending-careers] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending careers: {e}")


@router.post("/careers/{career_id}/review")
async def review_career(career_id: str, payload: CareerReviewActionPayload, http_req: Request):
    require_admin_role(http_req)
    try:
        if payload.action == "approve":
            update_data: Dict[str, Any] = {"review_status": "reviewed", "is_curated": True}
            if payload.custom_title and payload.custom_title.strip():
                update_data["title"] = payload.custom_title.strip()

            # Compute dual semantic vectors (title_vector, skills_vector, career_vector) upon approval
            # so approved AI/provisional careers immediately participate in Stage 1 pgvector recall.
            try:
                c_res = supabase_client.table("careers").select("title, description").eq("id", career_id).limit(1).execute()
                c_row = (c_res.data or [{}])[0]
                final_title = update_data.get("title") or c_row.get("title") or "Professional Career"
                final_desc = c_row.get("description") or ""

                cs_res = (
                    supabase_client.table("career_skills")
                    .select("skills(name)")
                    .eq("career_id", career_id)
                    .execute()
                )
                skill_names = [
                    r["skills"]["name"]
                    for r in (cs_res.data or [])
                    if r.get("skills") and r["skills"].get("name")
                ]
                if payload.custom_skills:
                    skill_names = [s.strip() for s in payload.custom_skills if s and s.strip()] or skill_names

                title_text = f"{final_title}. {final_desc}".strip()
                skills_text = (
                    f"Occupation: {final_title}. Core Competencies: {', '.join(skill_names)}."
                    if skill_names else title_text
                )
                vecs = await embedding_service.get_embeddings_batch([title_text, skills_text])
                if len(vecs) == 2 and vecs[0] and vecs[1]:
                    update_data["career_vector"] = vecs[0]
                    update_data["title_vector"] = vecs[0]
                    update_data["skills_vector"] = vecs[1]
            except Exception as vec_err:
                print(f"[admin-review-career] Vector computation warning: {vec_err}")

            try:
                supabase_client.table("careers").update(update_data).eq("id", career_id).execute()
            except Exception:
                # Fallback if dual vector columns (title_vector/skills_vector) are not yet migrated
                fallback_data = {
                    k: v for k, v in update_data.items()
                    if k not in ("title_vector", "skills_vector")
                }
                supabase_client.table("careers").update(fallback_data).eq("id", career_id).execute()

            try:
                supabase_client.table("career_skills").update({"review_status": "reviewed"}).eq("career_id", career_id).execute()
            except Exception:
                pass

            return {"status": "approved", "career_id": career_id, "message": "Career approved, embedded, and verified in taxonomy."}
        else:
            # Reject: mark rejected
            supabase_client.table("careers").update({"review_status": "rejected"}).eq("id", career_id).execute()
            return {"status": "rejected", "career_id": career_id, "message": "Career rejected and archived."}
    except Exception as e:
        print(f"[admin-review-career] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to review career: {e}")


# ---------------------------------------------------------------------------
# 3. Mentor Credential Verification
# ---------------------------------------------------------------------------
@router.get("/mentors")
async def list_mentors_for_admin(http_req: Request):
    require_admin_role(http_req)
    try:
        all_mentors = await mentorship_service.get_all_mentors()
        # Clean response
        mentors_list = []
        for m in all_mentors:
            mentors_list.append({
                "mentor_id": m.get("mentor_id"),
                "full_name": m.get("full_name"),
                "headline": m.get("headline"),
                "primary_domain": m.get("primary_domain"),
                "bio": m.get("bio"),
                "expertise_skills": m.get("expertise_skills", []),
                "weekly_hours": m.get("weekly_hours", 4),
                "is_verified": m.get("is_verified", True),
                "active_mentees": m.get("active_mentees_count", 0),
            })
        return {"mentors": mentors_list, "count": len(mentors_list)}
    except Exception as e:
        print(f"[admin-mentors] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch mentors: {e}")


@router.post("/mentors/{mentor_id}/verify")
async def toggle_mentor_verification(mentor_id: str, payload: MentorVerifyPayload, http_req: Request):
    require_admin_role(http_req)
    try:
        store = mentorship_service._ensure_store()
        for m in store.get("mentors", []):
            if m.get("mentor_id") == mentor_id:
                m["is_verified"] = payload.verified
                mentorship_service._save_store(store)
                break
        return {
            "status": "success",
            "mentor_id": mentor_id,
            "is_verified": payload.verified,
            "message": f"Mentor verification updated to {payload.verified}.",
        }
    except Exception as e:
        print(f"[admin-verify-mentor] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify mentor: {e}")


# ---------------------------------------------------------------------------
# 4. Moderation & Flagged Content (Durable File-Backed Store)
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
FLAGGED_FILE = os.path.join(DATA_DIR, "flagged_items.json")

def _load_flagged_items() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(FLAGGED_FILE):
        try:
            with open(FLAGGED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[admin-moderation] Error loading flagged items: {e}")
    initial = [
        {
            "id": "flag-sample-1",
            "item_type": "message",
            "sender_name": "Anonymous User",
            "target_context": "Direct Message to Mentor",
            "content_snippet": "Spam promotional link: http://buycrypto-token-fast.biz",
            "reason": "Suspected spam / external link solicitation",
            "created_at": "2026-11-01T08:15:00Z",
            "status": "pending_review",
        }
    ]
    _save_flagged_items(initial)
    return initial

def _save_flagged_items(items: List[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        print(f"[admin-moderation] Failed to save flagged items: {e}")

def record_flagged_item(item: Dict[str, Any]) -> None:
    items = _load_flagged_items()
    items.insert(0, item)
    _save_flagged_items(items)

# Expose _FLAGGED_ITEMS for backward-compatibility with imports
_FLAGGED_ITEMS = _load_flagged_items()


@router.get("/moderation/flagged")
async def get_flagged_content(http_req: Request):
    require_admin_role(http_req)
    items = _load_flagged_items()
    return {"flagged_items": items, "count": len(items)}


@router.post("/moderation/action")
async def act_on_moderation_item(payload: ModerationActionPayload, http_req: Request):
    require_admin_role(http_req)
    items = _load_flagged_items()
    if payload.action in ("dismiss", "delete"):
        filtered = [f for f in items if f["id"] != payload.item_id]
        _save_flagged_items(filtered)
        global _FLAGGED_ITEMS
        _FLAGGED_ITEMS = filtered
        msg = "Flag dismissed." if payload.action == "dismiss" else "Content removed and user warned."
        return {"status": payload.action, "message": msg}
    return {"status": "no_action"}


class FlagReportPayload(BaseModel):
    item_type: str = Field(..., pattern="^(message|pulse_post|recommendation|question|answer)$")
    item_id: str
    content_snippet: str
    target_context: Optional[str] = "Community Content"
    reason: Optional[str] = "Reported by user as irrelevant or inappropriate"


@router.post("/moderation/flag")
async def flag_item_for_moderation(payload: FlagReportPayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    new_flag = {
        "id": f"flag-{uuid.uuid4().hex[:8]}",
        "item_type": payload.item_type,
        "sender_name": f"User ({user_id[:8]}...)",
        "target_context": payload.target_context,
        "content_snippet": payload.content_snippet,
        "reason": payload.reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
    }
    record_flagged_item(new_flag)
    global _FLAGGED_ITEMS
    _FLAGGED_ITEMS = _load_flagged_items()
    return {
        "status": "reported",
        "flag_id": new_flag["id"],
        "message": "Content flagged for administrator review.",
    }


# ---------------------------------------------------------------------------
# 5. Content Ingestion & Reservoir Governance
# ---------------------------------------------------------------------------

class IngestionTriggerPayload(BaseModel):
    career_title: str
    skill_name: str
    skill_id: Optional[str] = None
    category: Optional[str] = "Core"


@router.get("/ingestion/overview")
async def get_ingestion_overview(http_req: Request):
    """Returns real-time metrics on the seeded curriculum reservoir in Supabase."""
    require_admin_role(http_req)
    try:
        res = supabase_client.table("micro_content").select("id, source_adapter, associated_skill_id, content, created_at").execute()
        rows = res.data or []
        total_lessons = len(rows)

        adapter_counts: Dict[str, int] = {}
        skill_ids = set()
        field_counts: Dict[str, int] = {}

        for r in rows:
            adapter = r.get("source_adapter") or "general"
            adapter_counts[adapter] = adapter_counts.get(adapter, 0) + 1
            if r.get("associated_skill_id"):
                skill_ids.add(r["associated_skill_id"])

            c_raw = r.get("content")
            if isinstance(c_raw, str):
                try:
                    c_dict = json.loads(c_raw)
                    f_id = c_dict.get("field_id") or "general"
                    field_counts[f_id] = field_counts.get(f_id, 0) + 1
                except Exception:
                    pass
            elif isinstance(c_raw, dict):
                f_id = c_raw.get("field_id") or "general"
                field_counts[f_id] = field_counts.get(f_id, 0) + 1

        return {
            "status": "success",
            "total_lessons": total_lessons,
            "unique_skills_seeded": len(skill_ids),
            "adapter_breakdown": adapter_counts,
            "field_breakdown": field_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ingestion stats: {str(e)}")


@router.get("/ingestion/lessons")
async def get_ingestion_lessons(http_req: Request, limit: int = 50):
    """Returns the most recently ingested lessons from the curriculum reservoir."""
    require_admin_role(http_req)
    try:
        from app.services.content_service import hydrate_micro_content_row
        res = (
            supabase_client.table("micro_content")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        hydrated = [hydrate_micro_content_row(r) for r in rows]
        return {
            "status": "success",
            "count": len(hydrated),
            "lessons": hydrated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reservoir lessons: {str(e)}")


@router.post("/ingestion/trigger")
async def trigger_ingestion_pipeline(payload: IngestionTriggerPayload, http_req: Request):
    """
    On-Demand Ingestion Worker (Live Supervisor Demonstration Endpoint):
    Polls the authoritative external adapters, applies dual semantic vector validation,
    generates 5 grounded MCQs with server-side shuffled keys, and seeds Supabase micro_content.
    Returns step-by-step telemetry logs.
    """
    require_admin_role(http_req)
    from app.services.content_service import ContentService
    from app.core.career_fields import classify_career_field

    logs: List[str] = []
    t_start = datetime.now(timezone.utc)
    logs.append(f"[{t_start.strftime('%H:%M:%S')}] Ingestion Worker Initialized for Career='{payload.career_title}', Skill='{payload.skill_name}'")

    field_meta = classify_career_field(payload.career_title)
    field_id = field_meta["field_id"]
    field_label = field_meta["label"]
    logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Career Field Resolved: {field_label} ('{field_id}')")

    svc = ContentService()
    try:
        # Step 1: Look up or resolve skill UUID
        resolved_skill_id = payload.skill_id
        if not resolved_skill_id:
            s_res = supabase_client.table("skills").select("id").ilike("name", f"%{payload.skill_name}%").limit(1).execute()
            if s_res.data:
                resolved_skill_id = s_res.data[0]["id"]
                logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Matched Canonical Skill UUID: {resolved_skill_id}")

        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Polling Authoritative Adapters for {field_id}...")

        # Step 2: Ingest and synthesize
        lesson = await svc.generate_dynamic_lesson_for_skill(
            skill_id=resolved_skill_id or str(uuid.uuid4()),
            skill_name=payload.skill_name,
            category=payload.category or "Core",
            career_title=payload.career_title,
            target_proficiency=20,
        )

        if not lesson:
            logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] FAILED: Candidate failed vector pedagogical gate or validation.")
            return {
                "status": "failed",
                "logs": logs,
                "lesson": None,
                "message": "Content did not meet strict pedagogical criteria or source was unreachable."
            }

        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Source Verified: '{lesson.get('source_name', 'Authoritative Source')}' ({lesson.get('source_adapter')})")
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Synthesized 5 Grounded MCQs. Checkpoint validation passed.")
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Committed to Supabase micro_content (ID: {lesson.get('id')})")

        # Record commit-style audit entry in Ingestion Ledger
        commit_rec = ingestion_batch_service.record_commit(
            career_title=payload.career_title,
            skill_name=payload.skill_name,
            sources=[{
                "name": lesson.get("source_name", "Authoritative Source"),
                "adapter": lesson.get("source_adapter", "web"),
                "url": lesson.get("source_url", ""),
                "trust_score": lesson.get("source_trust_score", 0.95),
            }],
            lesson_ids=[lesson.get("id")] if lesson.get("id") else [],
            message=f"Live Ingestion: Ingested '{lesson.get('title')}' for {payload.career_title}",
            author="Admin (Live Probe)",
            status="approved",
        )
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Ingestion Ledger Commit Created: #{commit_rec['commit_hash']}")

        return {
            "status": "success",
            "logs": logs,
            "lesson": lesson,
            "batch": commit_rec,
            "message": f"Successfully ingested and seeded lesson '{lesson.get('title')}' into Supabase reservoir."
        }
    except Exception as e:
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Error during ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail={"message": str(e), "logs": logs})


@router.get("/ingestion/priorities")
async def get_ingestion_priorities(http_req: Request):
    """Returns skills with registered user enrollment ranked by deficit demand and low lesson coverage."""
    require_admin_role(http_req)
    from app.services.ingestion_worker import ingestion_worker_service
    try:
        priorities = await ingestion_worker_service.get_enrolled_skills_priority()
        return {
            "status": "success",
            "count": len(priorities),
            "priorities": priorities,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch enrolled skill priorities: {str(e)}")


class NightlyBatchPayload(BaseModel):
    max_skills: Optional[int] = 5
    target_lessons_per_skill: Optional[int] = 3
    force_all: Optional[bool] = False


@router.post("/ingestion/run-nightly-batch")
async def run_nightly_batch_endpoint(payload: NightlyBatchPayload, http_req: Request):
    """
    Executes the Nightly Autonomous Ingestion Worker:
    Iterates over enrolled deficit skills, queries domain adapters, and seeds micro_content.
    """
    require_admin_role(http_req)
    from app.services.ingestion_worker import ingestion_worker_service
    try:
        result = await ingestion_worker_service.run_nightly_batch(
            max_skills=payload.max_skills or 5,
            target_lessons_per_skill=payload.target_lessons_per_skill or 3,
            force_all=payload.force_all or False,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nightly batch ingestion failed: {str(e)}")


@router.post("/daily-drop/run-batch-worker")
async def run_daily_drop_batch_endpoint(http_req: Request):
    """
    Executes the Daily Drop Personalization Worker for all registered learners:
    Pre-curates tomorrow's 5 primary + 5 reserve lessons from the seeded micro_content reservoir.
    """
    require_admin_role(http_req)
    from app.services.ingestion_worker import ingestion_worker_service
    try:
        result = await ingestion_worker_service.run_daily_drop_batch()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily Drop batch personalization failed: {str(e)}")


# ---------------------------------------------------------------------------
# 6. Ingestion Batches & Commit Audit Ledger
# ---------------------------------------------------------------------------

@router.get("/ingestion/batches")
async def list_ingestion_batches(http_req: Request):
    """Returns all git-commit style ingestion instances with source audits."""
    require_admin_role(http_req)
    batches = ingestion_batch_service.list_batches()
    return {"status": "success", "count": len(batches), "batches": batches}


@router.get("/ingestion/batches/{batch_id}")
async def get_ingestion_batch_detail(batch_id: str, http_req: Request):
    """Returns full details of a specific ingestion commit."""
    require_admin_role(http_req)
    batch = ingestion_batch_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Ingestion batch not found")
    return {"status": "success", "batch": batch}


class BatchStatusActionPayload(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|pending)$")


@router.post("/ingestion/batches/{batch_id}/status")
async def update_batch_status(batch_id: str, payload: BatchStatusActionPayload, http_req: Request):
    """Approves or rejects an entire ingestion commit and cascades to micro_content."""
    require_admin_role(http_req)
    res = ingestion_batch_service.set_batch_status(batch_id, payload.status)
    if not res:
        raise HTTPException(status_code=404, detail="Batch not found")
    action_label = "approved" if payload.status == "approved" else "disapproved (rejected)"
    return {
        "status": "success",
        "batch": res,
        "message": f"Ingestion commit {batch_id} marked as {action_label}.",
    }


class LessonEditPayload(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    concept_overview: Optional[str] = None
    practice_scenario: Optional[str] = None
    difficulty_level: Optional[int] = None
    quizzes: Optional[List[Dict[str, Any]]] = None
    associated_skill_id: Optional[str] = None


@router.put("/ingestion/lessons/{lesson_id}")
async def edit_ingested_lesson(lesson_id: str, payload: LessonEditPayload, http_req: Request):
    """Enables admin to inspect and edit ingested lessons, checkpoints, and skill bindings."""
    require_admin_role(http_req)
    try:
        res = ingestion_batch_service.edit_lesson(
            lesson_id=lesson_id,
            title=payload.title,
            summary=payload.summary,
            concept_overview=payload.concept_overview,
            practice_scenario=payload.practice_scenario,
            difficulty_level=payload.difficulty_level,
            quizzes=payload.quizzes,
            associated_skill_id=payload.associated_skill_id,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit lesson: {e}")




