import os
import sys
import json

path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_sprints.json")
with open(path, "r", encoding="utf-8") as f:
    sprints = json.load(f)

user_id = "9c4d483e-1296-4c24-8a78-fb09b2e30181"
matches = [s for s in sprints if s.get("user_id") == user_id]
print(f"Found {len(matches)} entries in daily_sprints.json:")
for m in matches:
    print(m)

