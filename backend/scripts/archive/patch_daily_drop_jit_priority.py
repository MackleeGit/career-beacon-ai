dds_path = "backend/app/services/daily_drop_service.py"
with open(dds_path, "r", encoding="utf-8") as f:
    text = f.read()

target_str = """        # If pool has fewer than 6, supplement from next priority skill in the same career
        if len(candidates) < 6 and len(skills) > 1:
            for alt_skill in skills:
                if alt_skill["id"] == target_skill_id:
                    continue
                alt_res = supabase_client.table("micro_content").select("*").eq(
                    "associated_skill_id", alt_skill["id"]
                ).limit(10).execute()
                for item in (alt_res.data or []):
                    if item["id"] in excluded or item["id"] in [c["id"] for c in candidates]:
                        continue
                    if self._verify_lesson_relevance(item, alt_skill["name"], alt_skill["id"], career_title):
                        candidates.append(item)
                    if len(candidates) >= 6:
                        break
                if len(candidates) >= 6:
                    break"""

replacement_str = """        # 3B. JIT Dynamic Generation for Target Skill: If candidate pool has < 3,
        # prioritize synthesizing lessons specifically for the focused deficit skill first.
        if len(candidates) < 3 and target_skill and target_skill_id:
            needed = 3 - len(candidates)
            for _ in range(needed):
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
                        timeout=14.0
                    )
                    if jit_lesson and isinstance(jit_lesson, dict) and jit_lesson.get("id"):
                        if self._verify_lesson_relevance(jit_lesson, target_skill_name, target_skill_id, career_title):
                            if jit_lesson["id"] not in [c["id"] for c in candidates]:
                                candidates.append(jit_lesson)
                except Exception as e:
                    logger.warning(f"JIT live source ingestion notice for {target_skill_name}: {e}")"""

# Normalize line endings
text_norm = text.replace("\r\n", "\n")
target_norm = target_str.replace("\r\n", "\n")
replacement_norm = replacement_str.replace("\r\n", "\n")

if target_norm in text_norm:
    text_norm = text_norm.replace(target_norm, replacement_norm, 1)
    with open(dds_path, "w", encoding="utf-8") as f:
        f.write(text_norm)
    print("Successfully prioritized JIT target generation in daily_drop_service.py")
else:
    print("Warning: target string not found in daily_drop_service.py")

