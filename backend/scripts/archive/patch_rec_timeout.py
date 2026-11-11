import os

path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "recommendation_service.py")
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

old_block = """                async def _paced_gen(s):
                    async with sem:
                        res = await self.content_service.generate_dynamic_lesson_for_skill(
                            skill_id=s["id"],
                            skill_name=s["name"],
                            category=s.get("category", "Core"),
                            career_title=career_title,
                            target_proficiency=s["proficiency"],
                            career_skill_context=career_skills_map.get(s["id"], {}),
                        )
                        await asyncio.sleep(0.2)
                        return res"""

new_block = """                async def _paced_gen(s):
                    async with sem:
                        try:
                            res = await asyncio.wait_for(
                                self.content_service.generate_dynamic_lesson_for_skill(
                                    skill_id=s["id"],
                                    skill_name=s["name"],
                                    category=s.get("category", "Core"),
                                    career_title=career_title,
                                    target_proficiency=s["proficiency"],
                                    career_skill_context=career_skills_map.get(s["id"], {}),
                                ),
                                timeout=7.0,
                            )
                            await asyncio.sleep(0.1)
                            return res
                        except asyncio.TimeoutError:
                            logger.warning(f"JIT generation timed out after 7.0s for '{s.get('name')}'; serving existing candidates.")
                            return None
                        except Exception as e:
                            logger.error(f"JIT generation error for '{s.get('name')}': {e}")
                            return None"""

if old_block in code:
    code = code.replace(old_block, new_block, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: patched recommendation_service.py timeout guard!")
else:
    print("Error: target block not found in recommendation_service.py")
