# backend/tests/recommendations/test_mentorship_module4.py
import os
import tempfile
import pytest

from app.services.mentorship_service import MentorshipService, ANTI_DESPERATION_THRESHOLD


@pytest.fixture
def isolated_mentorship_service(monkeypatch):
    """Provides a MentorshipService backed by a temporary JSON store so tests don't mutate production state."""
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(temp_path)

    import app.services.mentorship_service as ms_mod
    monkeypatch.setattr(ms_mod, "ECOSYSTEM_STORE_PATH", temp_path)

    svc = MentorshipService()
    yield svc

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_seeded_cross_industry_mentors_and_anti_desperation_gate(isolated_mentorship_service, monkeypatch):
    svc = isolated_mentorship_service
    mentors = await svc.get_all_mentors()
    assert len(mentors) >= 6
    domains = {m["primary_domain"] for m in mentors}
    assert "Software Architecture & Full-Stack" in domains
    assert "Finance, Accounting & Quantitative Analysis" in domains
    assert "Healthcare, Nursing & Clinical Practice" in domains
    assert "Culinary Arts, Hospitality & Skilled Trades" in domains

    # Mock learner context as a Fast Food / Culinary Operations learner
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Test Culinary Learner",
            "career_title": "Cooks, Fast Food",
            "career_description": "Prepare and cook food in a fast food restaurant with strict HACCP and inventory controls.",
            "all_skills": [
                {"skill_id": "s1", "name": "Food Safety & HACCP", "proficiency": 20, "category": "Culinary"},
                {"skill_id": "s2", "name": "Kitchen Operations", "proficiency": 30, "category": "Culinary"},
            ],
            "gap_skills": [
                {"skill_id": "s1", "name": "Food Safety & HACCP", "proficiency": 20, "category": "Culinary"},
                {"skill_id": "s2", "name": "Kitchen Operations", "proficiency": 30, "category": "Culinary"},
            ],
        },
    )

    match_res = await svc.match_mentors_for_learner("learner-culinary-1")
    assert match_res["anti_desperation_threshold"] == ANTI_DESPERATION_THRESHOLD
    assert len(match_res["matches"]) >= 1
    top_match = match_res["matches"][0]
    assert "Chef Antoine Moreau" in top_match["full_name"]
    assert "Food Safety & HACCP" in top_match["shared_gap_skills"]
    # Verify irrelevant mentors were filtered out by the Anti-Desperation Gate
    assert match_res["filtered_out_by_anti_desperation"] >= 1


@pytest.mark.asyncio
async def test_connection_dm_and_anti_double_booking_calendar(isolated_mentorship_service, monkeypatch):
    svc = isolated_mentorship_service
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Test SWE Learner",
            "career_title": "Backend Software Engineer",
            "career_description": "Build APIs and SQL databases.",
            "all_skills": [{"skill_id": "s1", "name": "SQL", "proficiency": 25, "category": "Tech"}],
            "gap_skills": [{"skill_id": "s1", "name": "SQL", "proficiency": 25, "category": "Tech"}],
        },
    )

    # 1. Request connection with Dr. Marcus Vance (seed-mentor-swe)
    conn = await svc.request_connection(
        learner_id="learner-swe-1",
        mentor_id="seed-mentor-swe",
        goal_note="Need help optimizing SQL queries.",
        auto_accept_demo=True,
    )
    assert conn["status"] == "accepted"

    # 2. Send a DM
    msg = svc.send_message(
        connection_id=conn["id"],
        sender_id="learner-swe-1",
        sender_role="learner",
        text="Looking forward to our SQL indexing review!",
    )
    assert msg["text"] == "Looking forward to our SQL indexing review!"
    history = svc.get_messages(conn["id"], "learner-swe-1")
    assert len(history) >= 2  # Welcome message + learner message

    # 3. Fetch available 45-min slots
    slots = await svc.get_available_slots("seed-mentor-swe", days_ahead=10)
    assert len(slots) > 0
    chosen_slot = slots[0]["slot_start_iso"]

    # 4. Book a 1-on-1 session
    booked = await svc.book_session(
        learner_id="learner-swe-1",
        mentor_id="seed-mentor-swe",
        slot_start_iso=chosen_slot,
        topic="SQL Indexing & Query Execution Plans",
        focus_skill="SQL",
        notes="Reviewing composite B-tree indexes.",
    )
    assert booked["status"] == "confirmed"
    assert booked["meeting_url"].startswith("https://meet.jit.si/CareerBeacon-")
    assert "calendar.google.com/calendar/render" in booked["google_calendar_url"]

    # 5. Verify Anti-Double-Booking: attempting to book the exact same slot must raise ValueError
    with pytest.raises(ValueError, match="Double-booking prevented"):
        await svc.book_session(
            learner_id="learner-swe-1",
            mentor_id="seed-mentor-swe",
            slot_start_iso=chosen_slot,
            topic="Duplicate Booking Attempt",
        )

    # 6. Verify RFC 5545 .ics calendar file generation with 24h & 15m VALARM reminders
    ics_text = svc.get_session_ics(booked["id"])
    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "TRIGGER:-PT24H" in ics_text
    assert "TRIGGER:-PT15M" in ics_text
    assert booked["meeting_url"] in ics_text


@pytest.mark.asyncio
async def test_qa_routing_and_pulse_feed(isolated_mentorship_service, monkeypatch):
    svc = isolated_mentorship_service
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Finance Learner",
            "career_title": "Financial Analyst",
            "career_description": "Corporate valuation and DCF modeling.",
            "all_skills": [{"skill_id": "s1", "name": "Financial Modeling", "proficiency": 30, "category": "Finance"}],
            "gap_skills": [{"skill_id": "s1", "name": "Financial Modeling", "proficiency": 30, "category": "Finance"}],
        },
    )

    q = await svc.ask_question(
        learner_id="learner-fin-1",
        title="How to handle negative free cash flow in terminal value?",
        body="When building a 5-year DCF for a high-growth firm, how do mentors normalize Year 5 FCF?",
        skill_tag="Financial Modeling",
        career_title="Financial Analyst",
        source_lesson_title="Discounted Cash Flow Foundations",
    )
    assert q["skill_tag"] == "Financial Modeling"

    answered = await svc.answer_question(
        question_id=q["id"],
        mentor_id="seed-mentor-fin",
        body="Extend the explicit forecast period to 10 years until margins stabilize, or use an exit EV/EBITDA multiple.",
    )
    assert len(answered["answers"]) == 1
    assert answered["answers"][0]["is_verified_mentor"] is True

    upvoted = svc.upvote_answer(q["id"], answered["answers"][0]["id"], "learner-fin-1")
    assert upvoted["upvotes"] == 2


@pytest.mark.asyncio
async def test_seven_tier_vector_centroid_firewall_blocks_inter_tier_leaking(isolated_mentorship_service, monkeypatch):
    """
    Verifies that the 7-Tier Vector Centroid Firewall separates occupations sharing
    generic words (e.g. 'Civil Engineer' vs 'Software Engineer', 'Financial Analyst'
    vs 'Data Science / Analytics Engineer') with zero hardcoded keyword maps.
    """
    svc = isolated_mentorship_service

    # Case 1: Civil Engineer (`engineering` tier) must match Engr. David Okafor (`engineering`)
    # and must NOT leak to Dr. Marcus Vance or Elena Rostova (`tech`).
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Civil Engineering Learner",
            "career_title": "Civil Engineer",
            "career_description": "Perform structural analysis, CAD blueprint design, fluid mechanics, and infrastructure project safety.",
            "all_skills": [
                {"skill_id": "e1", "name": "Structural Analysis", "proficiency": 25, "category": "Engineering"},
                {"skill_id": "e2", "name": "AutoCAD", "proficiency": 30, "category": "Engineering"},
            ],
            "gap_skills": [
                {"skill_id": "e1", "name": "Structural Analysis", "proficiency": 25, "category": "Engineering"},
                {"skill_id": "e2", "name": "AutoCAD", "proficiency": 30, "category": "Engineering"},
            ],
        },
    )
    eng_res = await svc.match_mentors_for_learner("learner-civil-eng")
    eng_names = [m["full_name"] for m in eng_res["matches"]]
    assert eng_res["learner_tier"] == "engineering"
    assert any("David Okafor" in name for name in eng_names)
    assert not any("Marcus Vance" in name for name in eng_names)
    assert not any("Elena Rostova" in name for name in eng_names)
    assert not any("Sarah Jenkins" in name for name in eng_names)

    # Case 2: Financial Analyst (`finance` tier) must match Jonathan Sterling, CFA (`finance`)
    # and must NOT leak to Elena Rostova (`tech` analytics) or Chef Antoine (`trades_safety`).
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Corporate Finance Learner",
            "career_title": "Financial Analyst",
            "career_description": "Build 3-statement financial models, DCF valuations, GAAP accounting audits, and variance budgets.",
            "all_skills": [
                {"skill_id": "f1", "name": "Financial Modeling", "proficiency": 20, "category": "Finance"},
                {"skill_id": "f2", "name": "Corporate Finance", "proficiency": 35, "category": "Finance"},
            ],
            "gap_skills": [
                {"skill_id": "f1", "name": "Financial Modeling", "proficiency": 20, "category": "Finance"},
                {"skill_id": "f2", "name": "Corporate Finance", "proficiency": 35, "category": "Finance"},
            ],
        },
    )
    fin_res = await svc.match_mentors_for_learner("learner-fin-analyst")
    fin_names = [m["full_name"] for m in fin_res["matches"]]
    assert fin_res["learner_tier"] == "finance"
    assert any("Jonathan Sterling" in name for name in fin_names)
    assert not any("Elena Rostova" in name for name in fin_names)
    assert not any("Antoine Moreau" in name for name in fin_names)

    # Case 3 (Dr. Tabulu's Middle-Ground / Interdisciplinary Question):
    # Bioinformatics Scientist sits on the Voronoi boundary between `science` and `tech`
    # (genomics/biostatistics + Python/SQL/Machine Learning pipelines).
    # `learner_active_tiers` bridges both `science` and `tech`, matching Elena Rostova
    # (ML/Data Science/Statistics) while still blocking unrelated tiers (`finance`, `trades_safety`, `engineering`).
    monkeypatch.setattr(
        svc,
        "_get_learner_context",
        lambda learner_id: {
            "learner_id": learner_id,
            "full_name": "Bioinformatics Learner",
            "career_title": "Bioinformatics Scientist",
            "career_description": "Analyze genomic sequencing datasets, PCR assay outputs, biostatistics, and computational biology pipelines using Python and SQL.",
            "all_skills": [
                {"skill_id": "b1", "name": "Python", "proficiency": 25, "category": "Bioinformatics"},
                {"skill_id": "b2", "name": "Statistics", "proficiency": 30, "category": "Bioinformatics"},
                {"skill_id": "b3", "name": "Machine Learning", "proficiency": 20, "category": "Bioinformatics"},
            ],
            "gap_skills": [
                {"skill_id": "b1", "name": "Python", "proficiency": 25, "category": "Bioinformatics"},
                {"skill_id": "b2", "name": "Statistics", "proficiency": 30, "category": "Bioinformatics"},
                {"skill_id": "b3", "name": "Machine Learning", "proficiency": 20, "category": "Bioinformatics"},
            ],
        },
    )
    bio_res = await svc.match_mentors_for_learner("learner-bioinformatics")
    bio_names = [m["full_name"] for m in bio_res["matches"]]
    assert "science" in bio_res["learner_active_tiers"]
    assert "tech" in bio_res["learner_active_tiers"]
    assert any("Elena Rostova" in name for name in bio_names)
    assert not any("Jonathan Sterling" in name for name in bio_names)
    assert not any("Antoine Moreau" in name for name in bio_names)


