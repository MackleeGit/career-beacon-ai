import os

path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "daily_drop_service.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update lines 206-225 in get_or_create_daily_drop
target_1 = """        if existing:
            # Rehydrate full lesson objects
            hydrated = await self._hydrate_drop(existing, user_id)
            # Self-healing: if cached drop has 3 valid lessons and strictly matches career, return it
            if hydrated.get("lessons") and len(hydrated["lessons"]) >= 3:
                prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
                cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
                c_title = self.rec_service.get_cached_career(cid).get("title", "") if cid else ""
                if all(_lesson_matches_career(l, c_title) for l in hydrated["lessons"]):
                    return hydrated

            # If existing drop was sparse (< 3) or contaminated, purge it from cache and re-curate fresh
            sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]

        # Curate fresh daily drop
        new_drop = await self._curate_daily_drop(user_id=user_id, sprint_date=today, priority_index=0)
        sprints.append(new_drop)
        _save_json_file(DAILY_SPRINTS_FILE, sprints)
        return await self._hydrate_drop(new_drop, user_id)"""

replacement_1 = """        if existing:
            # Check if existing drop was a valid calibrated drop
            has_target = existing.get("target_skill_id") is not None
            has_enough = len(existing.get("lesson_ids", [])) >= 3
            if has_target and has_enough:
                hydrated = await self._hydrate_drop(existing, user_id)
                if hydrated.get("lessons") and len(hydrated["lessons"]) >= 3:
                    prof_res = supabase_client.table("profiles").select("target_career_id").eq("id", user_id).execute()
                    cid = prof_res.data[0]["target_career_id"] if prof_res.data else None
                    c_title = self.rec_service.get_cached_career(cid).get("title", "") if cid else ""
                    if all(_lesson_matches_career(l, c_title) for l in hydrated["lessons"]):
                        return hydrated

            # If existing drop was an empty onboarding stub (< 3) or contaminated, purge it from cache
            sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]
            _save_json_file(DAILY_SPRINTS_FILE, sprints)

        # Curate fresh daily drop
        new_drop = await self._curate_daily_drop(user_id=user_id, sprint_date=today, priority_index=0)
        # ONLY cache to disk if it contains calibrated lessons for a real skill
        if new_drop.get("target_skill_id") and len(new_drop.get("lesson_ids", [])) > 0:
            sprints.append(new_drop)
            _save_json_file(DAILY_SPRINTS_FILE, sprints)
        return await self._hydrate_drop(new_drop, user_id)"""

# 2. Update self-healing skills auto-enrollment in _curate_daily_drop
target_2 = """        # Self-healing: if user is missing essential career skills, auto-enroll them
        enrolled_ids = {s["id"] for s in skills}
        missing_essential_ids = [
            sid for sid, meta in career_skills_map.items()
            if meta.get("importance") == "essential" and sid not in enrolled_ids
        ]
        if missing_essential_ids:
            try:
                all_skills_map = self.rec_service.get_cached_all_skills()
                auto_inserts = []
                for sid in missing_essential_ids:
                    sk = all_skills_map.get(sid)
                    if sk:
                        skills.append({
                            "id": sid,
                            "name": sk.get("name", "Core Skill"),
                            "category": sk.get("category", "Technical"),
                            "proficiency": 20,
                            "essential": True,
                            "tier": career_skills_map.get(sid, {}).get("tier") or 1,
                        })
                        auto_inserts.append({"user_id": user_id, "skill_id": sid, "proficiency": 20})
                if auto_inserts:
                    supabase_client.table("user_skills").insert(auto_inserts).execute()
            except Exception as e:
                logger.warning(f"Auto-backfill essential skills in daily drop notice: {e}")"""

replacement_2 = """        # Self-healing: if user is missing essential career skills, auto-enroll them
        enrolled_ids = {s["id"] for s in skills}
        missing_essential_ids = [
            sid for sid, meta in career_skills_map.items()
            if meta.get("importance") == "essential" and sid not in enrolled_ids
        ]
        # Fallback if no essential skills exist for this career: take top 5 by importance score
        if not missing_essential_ids and not enrolled_ids and career_skills_map:
            sorted_career_skills = sorted(
                career_skills_map.items(),
                key=lambda pair: pair[1].get("importance_score") or 0.0,
                reverse=True
            )
            missing_essential_ids = [sid for sid, _ in sorted_career_skills[:5]]

        if missing_essential_ids:
            try:
                all_skills_map = self.rec_service.get_cached_all_skills()
                auto_inserts = []
                for sid in missing_essential_ids:
                    sk = all_skills_map.get(sid)
                    if sk:
                        skills.append({
                            "id": sid,
                            "name": sk.get("name", "Core Skill"),
                            "category": sk.get("category", "Technical"),
                            "proficiency": 20,
                            "essential": True,
                            "tier": career_skills_map.get(sid, {}).get("tier") or 1,
                        })
                        auto_inserts.append({"user_id": user_id, "skill_id": sid, "proficiency": 20})
                if auto_inserts:
                    supabase_client.table("user_skills").insert(auto_inserts).execute()
            except Exception as e:
                logger.warning(f"Auto-backfill essential skills in daily drop notice: {e}")"""

for t, r in [(target_1, replacement_1), (target_2, replacement_2)]:
    t_crlf = t.replace("\n", "\r\n")
    r_crlf = r.replace("\n", "\r\n")
    if t in text:
        text = text.replace(t, r, 1)
        print("Replaced LF version.")
    elif t_crlf in text:
        text = text.replace(t_crlf, r_crlf, 1)
        print("Replaced CRLF version.")
    else:
        print("Target not found:", t[:40])

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

