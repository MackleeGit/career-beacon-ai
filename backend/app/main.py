import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import test, learner_onboarding, recommendations, mentor, admin
from app.middleware.auth_middleware import JWTAuthMiddleware

app = FastAPI(
    title="Career Beacon AI Engine",
    description="AI-Powered Micro-Learning and Mentorship Backend API service",
    version="1.0.0"
)

# 1. JWT authentication middleware – validates Supabase tokens on protected /api/* routes
app.add_middleware(JWTAuthMiddleware)

# 2. Configure CORS as the outermost layer so all responses (including OPTIONS preflights) carry CORS headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://careerbeacon.netlify.app",
    ],
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
if os.getenv("ENVIRONMENT") == "development":
    app.include_router(test.router)
app.include_router(learner_onboarding.router)
app.include_router(recommendations.router)
app.include_router(mentor.router)  # Mentor module 4 router
app.include_router(admin.router)   # Admin Command Center router

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Career Beacon AI Engine",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def start_keepalive_ping():
    """
    Prevents Render free-tier instance from sleeping (spins down after 15 min inactivity).
    Pings the public /health endpoint every 10 minutes (600 seconds).
    Automatically reads RENDER_EXTERNAL_URL injected by Render, or BACKEND_URL / PING_URL.
    """
    import asyncio
    import httpx

    ping_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BACKEND_URL") or os.getenv("PING_URL")
    if not ping_url:
        return

    target = f"{ping_url.rstrip('/')}/health" if not ping_url.endswith("/health") else ping_url

    async def _ping_loop():
        await asyncio.sleep(60)  # Initial grace delay after boot
        while True:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(target)
                    print(f"[keep-alive] Self-ping {target} -> Status {resp.status_code}")
            except Exception as e:
                print(f"[keep-alive] Self-ping notice: {e}")
            await asyncio.sleep(600)  # Every 10 minutes

    asyncio.create_task(_ping_loop())


@app.on_event("startup")
async def start_autonomous_maintenance_worker():
    """
    Autonomous Scheduled Ingestion & Daily Drop Maintenance Worker for Production (Render):
    1. Runs after an initial 5-minute boot grace period.
    2. Operates on a paced 4-hour duty cycle (`14,400s` break between cycles):
       - Executes a paced `run_nightly_batch(max_skills=4, inter_attempt_delay_sec=15.0)`
         that cross-references the Commit Ledger (`ingestion_batch_service`) so untouched
         skills are worked on first and already-worked skills rotate to the back of the queue.
       - Once per UTC calendar day, executes `run_daily_drop_batch()` across all enrolled
         learners so every learner's Daily Focus Drop is pre-computed and fresh.
    """
    import asyncio
    from datetime import datetime, timezone

    async def _maintenance_loop():
        await asyncio.sleep(300)  # Wait 5 minutes after startup before first background cycle
        last_daily_drop_date = None
        while True:
            try:
                from app.services.ingestion_worker import ingestion_worker_service

                # 1. Paced Commit-Ledger-Rotated Skill Ingestion Sweep (every 4h cycle)
                print("[autonomous-worker] Starting paced 4-hour skill ingestion rotation...")
                ing_res = await ingestion_worker_service.run_nightly_batch(
                    max_skills=4,
                    target_lessons_per_skill=3,
                    force_all=False,
                    inter_attempt_delay_sec=15.0,
                )
                print(
                    f"[autonomous-worker] Ingestion rotation completed: "
                    f"{ing_res.get('seeded_count', 0)} lesson(s) committed, "
                    f"{ing_res.get('rejected_count', 0)} rejected."
                )

                # 2. Daily Drop Personalization Batch (once per UTC day)
                today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if last_daily_drop_date != today_utc:
                    print(f"[autonomous-worker] Starting scheduled daily drop personalization batch for {today_utc}...")
                    drop_res = await ingestion_worker_service.run_daily_drop_batch()
                    last_daily_drop_date = today_utc
                    print(
                        f"[autonomous-worker] Daily drop batch completed: "
                        f"{drop_res.get('curated_count', 0)} learner drops synchronized."
                    )
            except Exception as e:
                print(f"[autonomous-worker] Maintenance loop notice: {e}")

            await asyncio.sleep(14400)  # 4-hour break between paced ingestion cycles

    asyncio.create_task(_maintenance_loop())


