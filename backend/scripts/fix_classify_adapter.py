import os

content_service_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")

with open(content_service_path, "r", encoding="utf-8") as f:
    code = f.read()

target = """    if "corporatefinance" in combined or "accounting" in combined:
        return "finance"
    if "youtube.com" in combined or "youtu.be" in combined:"""

replacement = """    if "investopedia.com" in combined or "corporatefinance" in combined:
        return "finance"
    if "youtube.com" in combined or "youtu.be" in combined:"""

if target in code:
    code = code.replace(target, replacement, 1)
    with open(content_service_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: Updated classify_source_adapter!")
else:
    print("Target not found!")

