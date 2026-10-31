# app/routers/mentor.py
"""
Mentor Onboarding, Semantic Matching & Ecosystem Router (Module 4)
------------------------------------------------------------------
Endpoints:
  POST /api/mentor/onboarding                    — Commits mentor profile, computes mentor_vector & registers in ecosystem
  GET  /api/mentor/skills                        — Returns paginated skills list for expertise picker
  GET  /api/mentor/profile/me                    — Returns full mentor profile & availability for MentorDashboard
  PATCH /api/mentor/profile/me                   — Updates mentor availability, capacity, headline, or bio
  GET  /api/mentor/matches                       — 2-Stage Anti-Desperation Semantic Mentor Matcher for learners
  GET  /api/mentor/connections                   — Lists connections for learner or mentor (with learner skill gap snapshot)
  POST /api/mentor/connections/request           — Sends connection request (or simulates demo acceptance)
  POST /api/mentor/connections/{conn_id}/respond — Mentor accepts or declines a pending connection request
  GET  /api/mentor/messages/{conn_id}            — Direct message history for a connection
  POST /api/mentor/messages                      — Send a direct message in an accepted connection
  GET  /api/mentor/pulse                         — Personalized Mentor Pulse feed
  POST /api/mentor/pulse                         — Mentor publishes a Pulse insight/event/advice post
  POST /api/mentor/pulse/{post_id}/like          — Toggle like on a Pulse post
  GET  /api/mentor/questions                     — Searchable Q&A Knowledge Base / Mentor Matched Q&A Inbox
  POST /api/mentor/questions                     — Learner asks a question (optionally linked to a Module 3 lesson)
  POST /api/mentor/questions/{q_id}/answer       — Mentor posts a verified answer
  POST /api/mentor/questions/{q_id}/answers/{a_id}/upvote — Upvote a helpful mentor answer
  GET  /api/mentor/{mentor_id}/slots             — Available 45-min slots for the next 10 days (double-booking filtered)
  POST /api/mentor/sessions/book                 — Books a 1-on-1 session (enforces anti-double-booking + Google Calendar/ICS)
  GET  /api/mentor/sessions                      — Lists sessions for learner or mentor
  POST /api/mentor/sessions/{session_id}/cancel  — Cancels a booked session
  POST /api/mentor/sessions/{session_id}/complete — Marks session complete + optional Post-Session Skill Endorsement (+15%)
  GET  /api/mentor/sessions/{session_id}/calendar.ics — Downloads RFC 5545 .ics calendar file with 24h & 15m VALARM reminders
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.mentorship_service import mentorship_service
from app.middleware.auth_middleware import get_verified_user_id

router = APIRouter(prefix="/api/mentor", tags=["Mentor"])

embedding_service = EmbeddingService()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class MentorSkillInput(BaseModel):
    skill_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="Technical Skills", max_length=60)


class MentorOnboardingRequest(BaseModel):
    primary_domain: str = Field(..., min_length=2, max_length=100)
    headline: str = Field(..., min_length=2, max_length=200)
    bio: str = Field(..., min_length=10, max_length=1000)
    weekly_hours: int = Field(default=4, ge=1, le=40)
    max_mentees: int = Field(default=5, ge=1, le=25)
    available_days: List[str] = Field(default_factory=list)
    preferred_time_window: str = Field(default="Evening", max_length=50)
    expertise: List[MentorSkillInput] = Field(..., min_length=1)


class MentorProfileUpdateRequest(BaseModel):
    primary_domain: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    weekly_hours: Optional[int] = None
    max_mentees: Optional[int] = None
    available_days: Optional[List[str]] = None
    preferred_time_window: Optional[str] = None
    expertise_skills: Optional[List[str]] = None


class ConnectionRequestPayload(BaseModel):
    mentor_id: str = Field(..., min_length=1)
    goal_note: str = Field(default="", max_length=500)
    auto_accept_demo: bool = Field(default=False)


class ConnectionRespondPayload(BaseModel):
    action: str = Field(..., pattern="^(accept|decline)$")


class DirectMessagePayload(BaseModel):
    connection_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1, max_length=2000)
    sender_role: str = Field(default="learner", pattern="^(learner|mentor)$")


class PulsePostCreatePayload(BaseModel):
    title: str = Field(..., min_length=3, max_length=180)
    post_type: str = Field(default="Industry Insight", max_length=60)
    body: str = Field(..., min_length=10, max_length=4000)
    skill_tags: List[str] = Field(default_factory=list)
    external_url: Optional[str] = None


class QuestionCreatePayload(BaseModel):
    title: str = Field(..., min_length=5, max_length=240)
    body: str = Field(..., min_length=5, max_length=3000)
    skill_tag: str = Field(default="General Career", max_length=100)
    career_title: Optional[str] = None
    source_lesson_title: Optional[str] = None


class QuestionAnswerPayload(BaseModel):
    body: str = Field(..., min_length=5, max_length=4000)


class SessionBookPayload(BaseModel):
    mentor_id: str = Field(..., min_length=1)
    slot_start_iso: str = Field(..., min_length=10)
    topic: str = Field(default="1-on-1 Career & Skill Mentorship Session", max_length=200)
    focus_skill: Optional[str] = None
    notes: str = Field(default="", max_length=1000)


class SessionCompletePayload(BaseModel):
    endorse_skill_name: Optional[str] = None
    feedback_note: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------------------
# POST /api/mentor/onboarding
# ---------------------------------------------------------------------------

@router.post("/onboarding")
async def mentor_onboarding(request: MentorOnboardingRequest, http_req: Request):
    """
    Commits mentor onboarding data to both `public.mentors` and the Mentorship Ecosystem store.
    """
    user_id = get_verified_user_id(http_req)

    # 1. Resolve all expertise skills against taxonomy
    resolved_skill_ids: List[str] = []
    skill_names: List[str] = []
    for sk in request.expertise:
        clean_name = sk.name.strip()
        skill_names.append(clean_name)
        real_skill_id = sk.skill_id

        if not real_skill_id:
            exact = (
                supabase_client.table("skills")
                .select("id")
                .ilike("name", clean_name)
                .limit(1)
                .execute()
            )
            if exact.data:
                real_skill_id = exact.data[0]["id"]
            else:
                new_sk = (
                    supabase_client.table("skills")
                    .insert({"name": clean_name, "category": sk.category})
                    .execute()
                )
                if not new_sk.data:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create skill record for '{sk.name}'.",
                    )
                real_skill_id = new_sk.data[0]["id"]

        resolved_skill_ids.append(real_skill_id)

    # 2. Build symmetrized mentor_vector embedding
    expertise_names = ", ".join(skill_names)
    embedding_text = (
        f"Domain: {request.primary_domain.strip()}. "
        f"Headline: {request.headline.strip()}. "
        f"Specialization: {request.bio.strip()}. "
        f"Core Skills: {expertise_names}."
    )
    try:
        mentor_vector = await embedding_service.get_embedding(embedding_text)
    except Exception as emb_err:
        print(f"[mentor-onboarding] Embedding error: {emb_err}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please try again.",
        )

    # 3. Persist into `mentors` table using live schema columns (id, profile_id, bio, expertise)
    mentor_db_payload = {
        "profile_id": user_id,
        "bio": request.bio.strip(),
        "expertise": f"{request.primary_domain.strip()} | {request.headline.strip()} | {expertise_names}",
    }
    try:
        existing_m = (
            supabase_client.table("mentors")
            .select("id")
            .eq("profile_id", user_id)
            .limit(1)
            .execute()
        )
        if existing_m.data:
            supabase_client.table("mentors").update(mentor_db_payload).eq("profile_id", user_id).execute()
        else:
            supabase_client.table("mentors").insert({"id": user_id, **mentor_db_payload}).execute()
    except Exception as db_err:
        print(f"[mentor-onboarding] mentors persistence error: {db_err}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save mentor profile. Please try again.",
        )

    # 4. Sync profile table (`bio`) & fetch mentor's full name
    full_name = "Industry Mentor"
    try:
        supabase_client.table("profiles").update({"bio": request.bio.strip()}).eq("id", user_id).execute()
        prof_res = supabase_client.table("profiles").select("full_name").eq("id", user_id).limit(1).execute()
        if prof_res.data and prof_res.data[0].get("full_name"):
            full_name = prof_res.data[0]["full_name"]
    except Exception as profile_err:
        print(f"[mentor-onboarding] profiles update warning: {profile_err}")

    # 5. Register extended availability & skills in the Mentorship Ecosystem store
    await mentorship_service.register_or_update_mentor(
        mentor_id=user_id,
        full_name=full_name,
        primary_domain=request.primary_domain.strip(),
        headline=request.headline.strip(),
        bio=request.bio.strip(),
        weekly_hours=request.weekly_hours,
        available_days=request.available_days,
        preferred_time_window=request.preferred_time_window,
        expertise_skills=skill_names,
        max_mentees=request.max_mentees,
    )

    return {
        "status": "success",
        "message": "Mentor profile successfully initialized and vectorized.",
        "mentor_id": user_id,
        "primary_domain": request.primary_domain,
        "skills_count": len(resolved_skill_ids),
    }


# ---------------------------------------------------------------------------
# GET /api/mentor/skills?q=<search>&limit=50&offset=0
# ---------------------------------------------------------------------------

@router.get("/skills")
async def list_skills(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    http_req: Request = None,
):
    limit = min(limit, 100)
    try:
        query = (
            supabase_client.table("skills")
            .select("id, name, category")
            .order("name")
            .range(offset, offset + limit - 1)
        )
        if q and q.strip():
            safe_q = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.ilike("name", f"{safe_q}%")

        res = query.execute()
        return {
            "skills": res.data or [],
            "count": len(res.data or []),
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch skills: {e}")


# ---------------------------------------------------------------------------
# GET & PATCH /api/mentor/profile/me
# ---------------------------------------------------------------------------

@router.get("/profile/me")
async def get_my_mentor_profile(http_req: Request):
    user_id = get_verified_user_id(http_req)
    mentors = await mentorship_service.get_all_mentors()
    me = next((m for m in mentors if m["mentor_id"] == user_id), None)
    if not me:
        # Fallback if mentor table row exists
        prof_res = supabase_client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        p = prof_res.data[0] if prof_res.data else {}
        me = await mentorship_service.register_or_update_mentor(
            mentor_id=user_id,
            full_name=p.get("full_name") or "Verified Mentor",
            primary_domain="Software Architecture & Full-Stack",
            headline=p.get("headline") or "Industry Mentor",
            bio="Experienced professional offering 1-on-1 career and technical guidance.",
            weekly_hours=p.get("weekly_hours") or 4,
            available_days=["Tue", "Thu"],
            preferred_time_window="Evening",
            expertise_skills=[],
            max_mentees=5,
        )
    return {"mentor": me}


@router.patch("/profile/me")
async def update_my_mentor_profile(payload: MentorProfileUpdateRequest, http_req: Request):
    user_id = get_verified_user_id(http_req)
    mentors = await mentorship_service.get_all_mentors()
    existing = next((m for m in mentors if m["mentor_id"] == user_id), {})

    updated = await mentorship_service.register_or_update_mentor(
        mentor_id=user_id,
        full_name=existing.get("full_name", "Industry Mentor"),
        primary_domain=payload.primary_domain or existing.get("primary_domain", "Software Architecture & Full-Stack"),
        headline=payload.headline or existing.get("headline", "Industry Mentor"),
        bio=payload.bio or existing.get("bio", ""),
        weekly_hours=payload.weekly_hours if payload.weekly_hours is not None else existing.get("weekly_hours", 4),
        available_days=payload.available_days if payload.available_days is not None else existing.get("available_days", ["Tue", "Thu"]),
        preferred_time_window=payload.preferred_time_window or existing.get("preferred_time_window", "Evening"),
        expertise_skills=payload.expertise_skills if payload.expertise_skills is not None else existing.get("expertise_skills", []),
        max_mentees=payload.max_mentees if payload.max_mentees is not None else existing.get("max_mentees", 5),
    )
    return {"status": "updated", "mentor": updated}


# ---------------------------------------------------------------------------
# GET /api/mentor/matches (2-Stage Anti-Desperation Matcher)
# ---------------------------------------------------------------------------

@router.get("/matches")
async def get_learner_mentor_matches(
    include_below_threshold: bool = False,
    http_req: Request = None,
):
    user_id = get_verified_user_id(http_req)
    return await mentorship_service.match_mentors_for_learner(
        learner_id=user_id,
        include_below_threshold=include_below_threshold,
    )


# ---------------------------------------------------------------------------
# Connections & Handshake Endpoints
# ---------------------------------------------------------------------------

@router.get("/connections")
async def list_connections(role: str = "learner", http_req: Request = None):
    user_id = get_verified_user_id(http_req)
    if role == "mentor":
        conns = mentorship_service.get_mentor_connections(user_id)
    else:
        conns = mentorship_service.get_learner_connections(user_id)
    return {"connections": conns}


@router.post("/connections/request")
async def request_mentor_connection(payload: ConnectionRequestPayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    try:
        conn = await mentorship_service.request_connection(
            learner_id=user_id,
            mentor_id=payload.mentor_id,
            goal_note=payload.goal_note,
            auto_accept_demo=payload.auto_accept_demo,
        )
        return {"status": "success", "connection": conn}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/connections/{connection_id}/respond")
async def respond_to_connection(
    connection_id: str,
    payload: ConnectionRespondPayload,
    http_req: Request,
):
    user_id = get_verified_user_id(http_req)
    try:
        conn = mentorship_service.respond_connection(
            connection_id=connection_id,
            mentor_id=user_id,
            action=payload.action,
        )
        return {"status": "success", "connection": conn}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ---------------------------------------------------------------------------
# Direct Messaging (DMs)
# ---------------------------------------------------------------------------

@router.get("/messages/{connection_id}")
async def get_connection_messages(connection_id: str, http_req: Request):
    user_id = get_verified_user_id(http_req)
    msgs = mentorship_service.get_messages(connection_id=connection_id, user_id=user_id)
    return {"messages": msgs}


@router.post("/messages")
async def send_connection_message(payload: DirectMessagePayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    try:
        msg = mentorship_service.send_message(
            connection_id=payload.connection_id,
            sender_id=user_id,
            sender_role=payload.sender_role,
            text=payload.text,
        )
        return {"status": "sent", "message": msg}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# ---------------------------------------------------------------------------
# Mentor Pulse Feed (LinkedIn-style Industry Updates & Events)
# ---------------------------------------------------------------------------

@router.get("/pulse")
async def get_mentor_pulse(post_type: Optional[str] = None, http_req: Request = None):
    user_id = get_verified_user_id(http_req)
    posts = mentorship_service.get_pulse_feed(learner_id=user_id, post_type=post_type)
    return {"posts": posts}


@router.post("/pulse")
async def create_pulse_post(payload: PulsePostCreatePayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    post = await mentorship_service.create_pulse_post(
        mentor_id=user_id,
        title=payload.title,
        post_type=payload.post_type,
        body=payload.body,
        skill_tags=payload.skill_tags,
        external_url=payload.external_url,
    )
    return {"status": "published", "post": post}


@router.post("/pulse/{post_id}/like")
async def toggle_pulse_like(post_id: str, http_req: Request):
    user_id = get_verified_user_id(http_req)
    try:
        post = mentorship_service.toggle_like_pulse_post(post_id=post_id, user_id=user_id)
        return {"status": "ok", "post": post}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ---------------------------------------------------------------------------
# Q&A Knowledge Base & Matched Mentor Inbox
# ---------------------------------------------------------------------------

@router.get("/questions")
async def list_questions(
    q: Optional[str] = None,
    skill_tag: Optional[str] = None,
    for_mentor: bool = False,
    http_req: Request = None,
):
    user_id = get_verified_user_id(http_req)
    questions = await mentorship_service.get_questions(
        search_query=q,
        skill_filter=skill_tag,
        mentor_id=user_id if for_mentor else None,
    )
    return {"questions": questions}


@router.post("/questions")
async def ask_mentor_question(payload: QuestionCreatePayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    question = mentorship_service.ask_question(
        learner_id=user_id,
        title=payload.title,
        body=payload.body,
        skill_tag=payload.skill_tag,
        career_title=payload.career_title,
        source_lesson_title=payload.source_lesson_title,
    )
    return {"status": "created", "question": question}


@router.post("/questions/{question_id}/answer")
async def answer_learner_question(
    question_id: str,
    payload: QuestionAnswerPayload,
    http_req: Request,
):
    user_id = get_verified_user_id(http_req)
    try:
        question = await mentorship_service.answer_question(
            question_id=question_id,
            mentor_id=user_id,
            body=payload.body,
        )
        return {"status": "answered", "question": question}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/questions/{question_id}/answers/{answer_id}/upvote")
async def upvote_question_answer(
    question_id: str,
    answer_id: str,
    http_req: Request,
):
    user_id = get_verified_user_id(http_req)
    try:
        ans = mentorship_service.upvote_answer(
            question_id=question_id,
            answer_id=answer_id,
            user_id=user_id,
        )
        return {"status": "ok", "answer": ans}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ---------------------------------------------------------------------------
# 1-on-1 Session Booking, Anti-Double-Booking & Calendar (.ics / Google Calendar)
# ---------------------------------------------------------------------------

@router.get("/{mentor_id}/slots")
async def get_mentor_available_slots(mentor_id: str, days_ahead: int = 10, http_req: Request = None):
    get_verified_user_id(http_req)
    try:
        slots = await mentorship_service.get_available_slots(mentor_id=mentor_id, days_ahead=days_ahead)
        return {"mentor_id": mentor_id, "slots": slots}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/sessions/book")
async def book_mentorship_session(payload: SessionBookPayload, http_req: Request):
    user_id = get_verified_user_id(http_req)
    try:
        session = await mentorship_service.book_session(
            learner_id=user_id,
            mentor_id=payload.mentor_id,
            slot_start_iso=payload.slot_start_iso,
            topic=payload.topic,
            focus_skill=payload.focus_skill,
            notes=payload.notes,
        )
        return {"status": "booked", "session": session}
    except ValueError as ve:
        # Conflict or validation failure
        status_code = 409 if "Double-booking" in str(ve) or "already has a session" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))


@router.get("/sessions")
async def list_mentorship_sessions(role: str = "learner", http_req: Request = None):
    user_id = get_verified_user_id(http_req)
    sessions = mentorship_service.get_sessions(user_id=user_id, role=role)
    return {"sessions": sessions}


@router.post("/sessions/{session_id}/cancel")
async def cancel_mentorship_session(session_id: str, http_req: Request):
    user_id = get_verified_user_id(http_req)
    try:
        sess = mentorship_service.cancel_session(session_id=session_id, user_id=user_id)
        return {"status": "cancelled", "session": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/sessions/{session_id}/complete")
async def complete_mentorship_session(
    session_id: str,
    payload: SessionCompletePayload,
    http_req: Request,
):
    user_id = get_verified_user_id(http_req)
    try:
        sess = mentorship_service.complete_session_and_endorse_skill(
            session_id=session_id,
            mentor_id=user_id,
            endorse_skill_name=payload.endorse_skill_name,
            feedback_note=payload.feedback_note,
        )
        return {"status": "completed", "session": sess}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/sessions/{session_id}/calendar.ics")
async def download_session_ics(session_id: str):
    """
    Returns an RFC 5545 iCalendar (.ics) file with valid Conference Room URL
    and two VALARM reminders (24 hours before and 15 minutes before).
    """
    try:
        ics_content = mentorship_service.get_session_ics(session_id=session_id)
        return Response(
            content=ics_content,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="CareerBeacon-Session-{session_id}.ics"'
            },
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
