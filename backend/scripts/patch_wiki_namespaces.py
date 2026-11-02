cs_path = "backend/app/services/content_service.py"
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

old_skip = 'any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:"))'
new_skip = 'any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:", "wikijournal", "user group", "project:", "wikiversity:", "wikibooks:", "draft:", "module:"))'

if old_skip in text:
    text = text.replace(old_skip, new_skip, 1)
    with open(cs_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Successfully filtered internal wiki user groups and namespaces in content_service.py")
else:
    print("Warning: old skip not found")

