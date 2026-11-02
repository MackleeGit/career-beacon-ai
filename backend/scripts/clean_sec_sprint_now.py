import os
import json

path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_sprints.json")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        sprints = json.load(f)
    clean = [s for s in sprints if s.get("user_id") != "f216bf54-ec34-451f-b29e-cec85b3e9f50"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    print(f"Purged stale sprint for secretary. Total left: {len(clean)}")
