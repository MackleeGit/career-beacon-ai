import os
import json

path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_sprints.json")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    clean = [s for s in data if s.get("target_skill_id") is not None and len(s.get("lesson_ids", [])) >= 3]
    print(f"Purged {len(data) - len(clean)} invalid/stub entries from daily_sprints.json. Retained {len(clean)} valid entries.")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)

