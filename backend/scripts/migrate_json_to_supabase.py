"""
backend/scripts/migrate_json_to_supabase.py
-------------------------------------------
Migrates data from local JSON files in backend/data/ to native Supabase tables:
- mentorship_ecosystem.json -> mentor_connections, mentor_messages, mentor_sessions
- user_streaks.json -> user_streaks
- daily_sprints.json -> daily_drops
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import supabase_client

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def migrate_streaks():
    fpath = DATA_DIR / "user_streaks.json"
    if not fpath.exists():
        print("user_streaks.json not found, skipping.")
        return
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else list(raw.values())
        rows = []
        for s in items:
            uid = s.get("user_id")
            if uid:
                rows.append({
                    "user_id": uid,
                    "current_streak": s.get("current_streak", 0),
                    "longest_streak": s.get("longest_streak", 0),
                    "last_activity_date": s.get("last_active_date") or s.get("last_activity_date"),
                    "freeze_count": s.get("freeze_count", 0),
                })
        if rows:
            res = supabase_client.table("user_streaks").upsert(rows).execute()
            print(f"Successfully migrated {len(rows)} user streaks to Supabase.")
    except Exception as e:
        print(f"user_streaks migration notice (table may need to be created first): {e}")

def migrate_mentorship():
    fpath = DATA_DIR / "mentorship_ecosystem.json"
    if not fpath.exists():
        print("mentorship_ecosystem.json not found, skipping.")
        return
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        
        # 1. Connections
        conns = data.get("connections", [])
        conn_list = conns if isinstance(conns, list) else list(conns.values())
        conn_rows = []
        for c in conn_list:
            if c.get("mentor_id") and c.get("learner_id"):
                conn_rows.append({
                    "id": c.get("id"),
                    "mentor_id": c.get("mentor_id"),
                    "learner_id": c.get("learner_id"),
                    "status": c.get("status", "accepted"),
                    "initial_message": c.get("goal_note") or c.get("initial_message"),
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                })
        if conn_rows:
            supabase_client.table("mentor_connections").upsert(conn_rows).execute()
            print(f"Successfully migrated {len(conn_rows)} mentorship connections to Supabase.")

        # 2. Messages
        msgs = data.get("messages", [])
        msg_list = msgs if isinstance(msgs, list) else []
        msg_rows = []
        for m in msg_list:
            if m.get("connection_id") and m.get("sender_id"):
                msg_rows.append({
                    "id": m.get("id"),
                    "connection_id": m.get("connection_id"),
                    "sender_id": m.get("sender_id"),
                    "recipient_id": m.get("recipient_id") or m.get("sender_id"), # fallback if not stored
                    "content": m.get("text") or m.get("content", ""),
                    "is_read": m.get("is_read", False),
                    "created_at": m.get("created_at"),
                })
        if msg_rows:
            for i in range(0, len(msg_rows), 50):
                supabase_client.table("mentor_messages").upsert(msg_rows[i : i + 50]).execute()
            print(f"Successfully migrated {len(msg_rows)} mentorship messages to Supabase.")

        # 3. Sessions
        sessions = data.get("sessions", [])
        sess_list = sessions if isinstance(sessions, list) else list(sessions.values())
        sess_rows = []
        for s in sess_list:
            if s.get("mentor_id") and s.get("learner_id"):
                sess_rows.append({
                    "id": s.get("id"),
                    "connection_id": s.get("connection_id"),
                    "mentor_id": s.get("mentor_id"),
                    "learner_id": s.get("learner_id"),
                    "slot_start_iso": s.get("slot_start_iso"),
                    "slot_end_iso": s.get("slot_end_iso"),
                    "status": s.get("status", "confirmed"),
                    "meet_url": s.get("meeting_url") or s.get("meet_url"),
                    "created_at": s.get("created_at"),
                })
        if sess_rows:
            supabase_client.table("mentor_sessions").upsert(sess_rows).execute()
            print(f"Successfully migrated {len(sess_rows)} scheduled sessions to Supabase.")

    except Exception as e:
        print(f"mentorship migration notice (tables may need to be created first): {e}")

def migrate_daily_drops():
    fpath = DATA_DIR / "daily_sprints.json"
    if not fpath.exists():
        print("daily_sprints.json not found, skipping.")
        return
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else list(raw.values())
        rows = []
        for s in items:
            uid = s.get("user_id")
            date = s.get("sprint_date") or s.get("date")
            if uid and date:
                rows.append({
                    "user_id": uid,
                    "drop_date": date,
                    "status": "completed" if s.get("is_completed") else "in_progress",
                    "payload": s,
                })
        if rows:
            for i in range(0, len(rows), 50):
                supabase_client.table("daily_drops").upsert(rows[i : i + 50]).execute()
            print(f"Successfully migrated {len(rows)} daily drop bundles to Supabase.")
    except Exception as e:
        print(f"daily_drops migration notice (table may need to be created first): {e}")

def main():
    print("=== Starting Local JSON -> Supabase Data Migration ===")
    migrate_streaks()
    migrate_mentorship()
    migrate_daily_drops()
    print("=== Migration Execution Completed ===")

if __name__ == "__main__":
    main()
