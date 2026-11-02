import os
import sys
import json

data_file = os.path.join(os.path.dirname(__file__), "..", "data", "daily_sprints.json")
if os.path.exists(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total entries in daily_sprints.json: {len(data)}")
    for entry in data:
        print(f"User: {entry.get('user_id')}, Date: {entry.get('sprint_date')}, Skill: {entry.get('target_skill_name')}, Active IDs: {entry.get('active_lesson_ids')}, Lesson IDs: {entry.get('lesson_ids')}")

