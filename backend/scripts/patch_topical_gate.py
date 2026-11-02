import os

path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "daily_drop_service.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = """        # 1B. Strict Career Boundary check: Reject lessons explicitly branded for another career
        if not _lesson_matches_career(lesson, career_title):
            return False

        # 2. Associated skill binding"""

replacement = """        # 1B. Strict Career Boundary check: Reject lessons explicitly branded for another career
        if not _lesson_matches_career(lesson, career_title):
            return False

        # 1C. Anti-Spurious Topical Gate: Reject ancient history/mythology lessons for modern workplace skills
        title_lower = (lesson.get("title") or "").lower()
        hist_flags = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore")
        if any(h in title_lower for h in hist_flags) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth")):
            return False

        # 2. Associated skill binding"""

if target in text:
    text = text.replace(target, replacement, 1)
    print("Patched daily_drop_service.py (LF)")
elif target.replace("\n", "\r\n") in text:
    text = text.replace(target.replace("\n", "\r\n"), replacement.replace("\n", "\r\n"), 1)
    print("Patched daily_drop_service.py (CRLF)")
else:
    print("Target not found in daily_drop_service.py")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
