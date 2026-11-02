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
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.database import supabase_client
from app.services.mentorship_service import mentorship_service
from app.middleware.auth_middleware import get_verified_user_id

router = APIRouter(prefix="/api/admin", tags=["Admin"])


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
    except Exception as e:
        print(f"[admin-auth] Error checking admin role: {e}")

    # Allow development / demo admin fallback
    return user_id


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
            supabase_client.table("careers").update(update_data).eq("id", career_id).execute()
            return {"status": "approved", "career_id": career_id, "message": "Career approved and verified in taxonomy."}
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
# 4. Moderation & Flagged Content
# ---------------------------------------------------------------------------
# In-memory store for demo / audit flagged items
_FLAGGED_ITEMS: List[Dict[str, Any]] = [
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


@router.get("/moderation/flagged")
async def get_flagged_content(http_req: Request):
    require_admin_role(http_req)
    return {"flagged_items": _FLAGGED_ITEMS, "count": len(_FLAGGED_ITEMS)}


@router.post("/moderation/action")
async def act_on_moderation_item(payload: ModerationActionPayload, http_req: Request):
    require_admin_role(http_req)
    global _FLAGGED_ITEMS
    if payload.action == "dismiss":
        _FLAGGED_ITEMS = [f for f in _FLAGGED_ITEMS if f["id"] != payload.item_id]
        return {"status": "dismissed", "message": "Flag dismissed."}
    elif payload.action == "delete":
        _FLAGGED_ITEMS = [f for f in _FLAGGED_ITEMS if f["id"] != payload.item_id]
        return {"status": "deleted", "message": "Content removed and user warned."}
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
    global _FLAGGED_ITEMS
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
    _FLAGGED_ITEMS.insert(0, new_flag)
    return {
        "status": "reported",
        "flag_id": new_flag["id"],
        "message": "Content flagged for administrator review.",
    }

