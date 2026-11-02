import re

cs_path = "backend/app/services/content_service.py"
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Remove string check for secretar/administrat in resolve_career_domain
old_check = '''        # Deterministic check for administrative/secretarial occupations
        low_title = (career_title or "").lower()
        if any(k in low_title for k in ("secretar", "administrat", "office assistant", "clerk", "receptionist", "executive assistant")):
            return "business_admin"\n\n'''
text = text.replace(old_check, "")

# 2. Enrich tech anchor
old_tech = '"tech": "software programming technology web development cloud computer code database api network algorithms",'
new_tech = '"tech": "software programming technology web development cloud computer code database api network algorithms operating systems sysadmin linux unix server infrastructure",'
text = text.replace(old_tech, new_tech)

# 3. Add semantic domain verification in _fetch_open_textbook
old_validation_block = '''                                if validate_source_content(slice_text, skill_name):
                                    return {'''

new_validation_block = '''                                if validate_source_content(slice_text, skill_name):
                                    # Semantic Domain Verification: Verify textbook belongs to same occupational domain
                                    tb_domain = await self.resolve_career_domain(page_title, slice_text[:300])
                                    tgt_domain = await self.resolve_career_domain(career_title, skill_name)
                                    if tgt_domain not in {"general", ""} and tb_domain not in {"general", ""} and tb_domain != tgt_domain:
                                        logger.info(f"Semantically rejecting open textbook '{page_title}' ({tb_domain}) for career '{career_title}' ({tgt_domain})")
                                        continue
                                    return {'''

text = text.replace(old_validation_block, new_validation_block)

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Applied semantic domain verification successfully")

