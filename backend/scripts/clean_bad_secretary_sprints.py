import os
import json

path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_sprints.json")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        sprints = json.load(f)
    bad_set = {
        '18a4de4e-7fe0-431a-b371-1095a2a90d77',
        '1eadc0c7-e1ef-448c-a742-46e254e73bd0',
        '72822125-4dd4-4713-8904-39242bee1499'
    }
    cleaned = []
    for s in sprints:
        ids = s.get("lesson_ids") or []
        if any(i in bad_set for i in ids):
            print("Purged sprint with bad secretary lesson:", s.get("user_id"), s.get("target_skill_name"))
        else:
            cleaned.append(s)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    print(f"Purged {len(sprints) - len(cleaned)} sprints.")
