import os

cs_path = os.path.abspath("backend/app/services/content_service.py")
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Remove _synthesize_autonomous_lesson method
target_start = "    async def _synthesize_autonomous_lesson("
target_end = "    async def generate_dynamic_lesson_for_skill("

assert target_start in text, "target_start not found"
assert target_end in text, "target_end not found"

part1 = text[:text.index(target_start)]
part2 = text[text.index(target_end):]

# 2. In part2, ensure generate_dynamic_lesson_for_skill strictly checks live_source
old_gen_block = """        if not live_source or not live_source.get("source_url") or not live_source.get("raw_text") or not validate_source_content(live_source.get("raw_text", ""), skill_name):
            logger.info(f"Live web source unseeded for '{skill_name}' ({career_title}); engaging Autonomous Curriculum Synthesis.")
            return await self._synthesize_autonomous_lesson(
                skill_id=skill_id,
                skill_name=skill_name,
                category=category,
                career_title=career_title,
                target_proficiency=target_proficiency,
                career_skill_context=career_skill_context,
            )"""

new_gen_block = """        if not live_source or not live_source.get("source_url") or not live_source.get("raw_text") or not validate_source_content(live_source.get("raw_text", ""), skill_name):
            logger.warning(f"No verifiable real educational source found for '{skill_name}' ({career_title}).")
            return None"""

assert old_gen_block in part2, "old_gen_block not found"
part2 = part2.replace(old_gen_block, new_gen_block)

full_cleaned = part1 + part2

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(full_cleaned)

print("PASS: _synthesize_autonomous_lesson completely removed. Live real sources strictly enforced.")

