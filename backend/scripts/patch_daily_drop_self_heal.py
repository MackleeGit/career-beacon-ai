import os

path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "daily_drop_service.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update lines 200-215
target_1 = """        if existing:
            # Rehydrate full lesson objects
            return await self._hydrate_drop(existing, user_id)"""

replacement_1 = """        if existing:
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
            sprints = [s for s in sprints if not (s.get("user_id") == user_id and s.get("sprint_date") == today)]"""

# 2. Update lines 460-481
target_2 = """        # 3C. JIT Dynamic Generation: If candidate pool is insufficient (< 3),
        # attempt to fetch and ingest a real domain-grounded lesson for the target skill.
        if len(candidates) < 3 and target_skill and target_skill_id:
            try:
                jit_lesson = await asyncio.wait_for(
                    self.rec_service.content_service.generate_dynamic_lesson_for_skill(
                        skill_id=target_skill_id,
                        skill_name=target_skill_name,
                        category=target_skill.get("category", "Core"),
                        career_title=career_title,
                        target_proficiency=target_skill.get("proficiency", 20),
                        career_skill_context=career_skills_map.get(target_skill_id, {})
                    ),
                    timeout=8.0
                )
                if jit_lesson and isinstance(jit_lesson, dict) and jit_lesson.get("id"):
                    if self._verify_lesson_relevance(jit_lesson, target_skill_name, target_skill_id, career_title):
                        if jit_lesson["id"] not in [c["id"] for c in candidates]:
                            candidates.append(jit_lesson)
            except Exception as e:
                logger.warning(f"JIT live source ingestion notice for {target_skill_name}: {e}")"""

replacement_2 = """        # 3C. JIT Dynamic Generation: If candidate pool is insufficient (< 3),
        # dynamically synthesize real domain-grounded lessons across the learner's essential skills.
        if len(candidates) < 3 and skills:
            skills_to_try = [target_skill] + [s for s in skills if s.get("id") != target_skill_id]
            for sk in skills_to_try:
                if len(candidates) >= 3:
                    break
                s_id = sk.get("id")
                s_name = sk.get("name")
                if not s_id or not s_name:
                    continue
                try:
                    jit_lesson = await asyncio.wait_for(
                        self.rec_service.content_service.generate_dynamic_lesson_for_skill(
                            skill_id=s_id,
                            skill_name=s_name,
                            category=sk.get("category", "Core"),
                            career_title=career_title,
                            target_proficiency=sk.get("proficiency", 20),
                            career_skill_context=career_skills_map.get(s_id, {})
                        ),
                        timeout=14.0
                    )
                    if jit_lesson and isinstance(jit_lesson, dict) and jit_lesson.get("id"):
                        if self._verify_lesson_relevance(jit_lesson, s_name, s_id, career_title):
                            if jit_lesson["id"] not in [c["id"] for c in candidates]:
                                candidates.append(jit_lesson)
                except Exception as e:
                    logger.warning(f"JIT live source ingestion notice for {s_name}: {e}")"""

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

