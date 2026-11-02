import os
import sys
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import supabase_client
from app.services.mentorship_service import mentorship_service

def audit_database():
    print("=" * 70)
    print("CAREER BEACON DATABASE SANITY & INTEGRITY AUDIT")
    print("=" * 70)

    # 1. Profiles & Roles
    p_res = supabase_client.table("profiles").select("id, role, username, email, full_name, created_at").execute()
    profiles = p_res.data or []
    roles = {}
    missing_username = []
    missing_email = []
    for p in profiles:
        r = p.get("role") or "unassigned"
        roles[r] = roles.get(r, 0) + 1
        if not p.get("username"):
            missing_username.append(p.get("id"))
        if not p.get("email"):
            missing_email.append(p.get("id"))

    print(f"\n[1] PROFILES ({len(profiles)} total)")
    for r, cnt in sorted(roles.items()):
        print(f"    - Role '{r}': {cnt}")
    print(f"    - Missing username: {len(missing_username)}")
    print(f"    - Missing email: {len(missing_email)}")
    print("    Sample users:")
    for p in profiles[:8]:
        print(f"      * {p.get('username') or '(no user)'} | {p.get('email')} | role: {p.get('role')} | id: {p.get('id')[:8]}...")

    # 2. Careers Catalog
    c_res = supabase_client.table("careers").select("id, title, source_origin, review_status, created_at").execute()
    careers = c_res.data or []
    origins = {}
    review_statuses = {}
    title_map = {}
    plural_candidates = []

    for c in careers:
        t = (c.get("title") or "").strip()
        tl = t.lower()
        title_map[tl] = title_map.get(tl, 0) + 1
        o = c.get("source_origin") or "unknown"
        origins[o] = origins.get(o, 0) + 1
        st = c.get("review_status") or "unreviewed"
        review_statuses[st] = review_statuses.get(st, 0) + 1

        # Check for plural endings (excluding standard singulars like physics, business, analysis, etc.)
        if t.endswith("s") and not t.endswith("ss") and not t.endswith("ics") and not t.endswith("us") and not t.endswith("is"):
            plural_candidates.append(t)

    duplicates = {k: v for k, v in title_map.items() if v > 1}

    print(f"\n[2] CAREERS CATALOG ({len(careers)} total)")
    print(f"    - Source breakdown: {origins}")
    print(f"    - Review status: {review_statuses}")
    print(f"    - Exact duplicate titles: {len(duplicates)}")
    if duplicates:
        for d, cnt in list(duplicates.items())[:5]:
            print(f"      * '{d}': {cnt} occurrences")
    print(f"    - Potential plural titles flagged: {len(plural_candidates)}")
    if plural_candidates:
        print(f"      * Samples: {plural_candidates[:5]}")

    # 3. Skills Taxonomy & Mappings
    sk_res = supabase_client.table("skills").select("id, name, category").execute()
    skills = sk_res.data or []
    cs_res = supabase_client.table("career_skills").select("career_id, skill_id, importance").execute()
    career_skills = cs_res.data or []
    importance_map = {}
    for cs in career_skills:
        imp = cs.get("importance") or "unassigned"
        importance_map[imp] = importance_map.get(imp, 0) + 1

    print(f"\n[3] SKILLS TAXONOMY ({len(skills)} distinct skills, {len(career_skills)} career mappings)")
    print(f"    - Importance distribution: {importance_map}")

    # 4. User Skills & Evidence
    us_res = supabase_client.table("user_skills").select("user_id, skill_id, proficiency, evidence_source").execute()
    user_skills = us_res.data or []
    evidence_map = {}
    users_with_skills = set()
    for us in user_skills:
        users_with_skills.add(us.get("user_id"))
        ev = us.get("evidence_source") or "none"
        evidence_map[ev] = evidence_map.get(ev, 0) + 1

    print(f"\n[4] USER SKILLS ({len(user_skills)} calibrated rows across {len(users_with_skills)} learners)")
    print(f"    - Evidence sources: {evidence_map}")

    # 5. Mentorship Ecosystem (Store & Tables)
    m_db_res = supabase_client.table("mentors").select("*").execute()
    db_mentors = m_db_res.data or []
    store = mentorship_service._ensure_store()
    store_mentors = store.get("mentors", [])
    store_sessions = store.get("sessions", [])
    store_conns = store.get("connections", [])
    store_questions = store.get("questions", [])

    print(f"\n[5] MENTORSHIP ECOSYSTEM")
    print(f"    - Mentors in Supabase DB: {len(db_mentors)}")
    if db_mentors:
        print(f"      * DB Mentors sample columns: {list(db_mentors[0].keys())}")
        for dbm in db_mentors[:3]:
            print(f"      * DB Mentor: id={dbm.get('id')}, profile_id={dbm.get('profile_id')}")
    print(f"    - Mentors in Ecosystem Store: {len(store_mentors)}")
    print(f"      * Seeded mentors: {sum(1 for m in store_mentors if m.get('is_seeded'))}")
    print(f"      * Organic mentors: {sum(1 for m in store_mentors if not m.get('is_seeded'))}")
    print(f"    - Connections count: {len(store_conns)}")
    for c in store_conns[:5]:
        print(f"      * Connection {c.get('id')}: status={c.get('status')}, learner={str(c.get('learner_id'))[:8]}, mentor={str(c.get('mentor_id'))[:8]}")
    print(f"    - 1-on-1 Sessions count: {len(store_sessions)}")
    for s in store_sessions[:5]:
        print(f"      * Session {s.get('id')}: status={s.get('status')}, topic='{s.get('topic')}', time={s.get('slot_start_iso')}")
    print(f"    - Q&A Questions count: {len(store_questions)}")

    # Summary
    print("\n" + "=" * 70)
    is_clean = (
        len(duplicates) == 0
        and len(missing_email) == 0
        and len(careers) >= 700
        and len(skills) >= 100
    )
    print(f"DATABASE HEALTH SUMMARY: {'CLEAN & HEALTHY' if is_clean else 'ATTENTION NEEDED'}")
    print("=" * 70)

if __name__ == "__main__":
    audit_database()
