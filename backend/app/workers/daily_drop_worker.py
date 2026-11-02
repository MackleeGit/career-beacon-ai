"""
Nightly Daily Focus Drop Background Worker
------------------------------------------
Pre-warms and curates the daily 3-lesson drop for all active learners before peak morning hours.
Eliminates on-demand LLM latency and ensures 0ms response time upon app launch.

Usage:
    python -m app.workers.daily_drop_worker
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.core.database import supabase_client
from app.services.daily_drop_service import DailyDropService, _today_str

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [daily_drop_worker] %(message)s",
)
logger = logging.getLogger("career_beacon.daily_drop_worker")


async def run_nightly_curation_worker(active_window_days: int = 14) -> Dict[str, Any]:
    """
    Scans profiles for learners with an active target career, computes today's
    daily drop, and pre-warms JIT content generation if micro_content is sparse.
    """
    start_time = time.time()
    today = _today_str()
    logger.info(f"Starting Nightly Daily Drop Worker for date: {today}")

    # Fetch active learners with assigned careers
    prof_res = (
        supabase_client.table("profiles")
        .select("id, full_name, email, target_career_id, updated_at")
        .not_.is_("target_career_id", "null")
        .execute()
    )
    learners = prof_res.data or []
    logger.info(f"Found {len(learners)} registered learners with target careers.")

    service = DailyDropService()
    success_count = 0
    failure_count = 0
    generated_count = 0

    for learner in learners:
        user_id = learner["id"]
        career_id = learner.get("target_career_id")
        try:
            t0 = time.time()
            drop = await service.get_or_create_daily_drop(user_id)
            elapsed_ms = (time.time() - t0) * 1000
            lesson_count = len(drop.get("lessons", []))
            target_skill = drop.get("target_skill_name", "Core Skill")
            logger.info(
                f"Curated drop for user {user_id[:8]}... ({target_skill}) - "
                f"{lesson_count}/3 lessons in {elapsed_ms:.1f}ms"
            )
            success_count += 1
            if lesson_count > 0:
                generated_count += lesson_count
        except Exception as e:
            logger.error(f"Failed to curate drop for user {user_id}: {e}")
            failure_count += 1

    total_time = time.time() - start_time
    summary = {
        "sprint_date": today,
        "total_learners_scanned": len(learners),
        "successful_curations": success_count,
        "failed_curations": failure_count,
        "total_lessons_delivered": generated_count,
        "execution_seconds": round(total_time, 2),
    }
    logger.info(f"Nightly curation worker completed in {total_time:.2f}s: {summary}")
    return summary


def main():
    asyncio.run(run_nightly_curation_worker())


if __name__ == "__main__":
    main()

