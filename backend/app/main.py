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
    Autonomous Daily Maintenance Worker for Production (Render):
    1. Runs after an initial 5-minute boot grace period.
    2. Executes daily drop batch personalization across all enrolled learners once every 24 hours.
    3. Guarantees that even if no user logs in, every enrolled learner's drop is pre-computed and fresh.
    """
    import asyncio
    async def _maintenance_loop():
        await asyncio.sleep(300)  # Wait 5 minutes after startup before first background batch
        while True:
            try:
                from app.services.ingestion_worker import ingestion_worker_service
                print("[autonomous-worker] Starting scheduled daily drop personalization batch...")
                res = await ingestion_worker_service.run_daily_drop_batch()
                print(f"[autonomous-worker] Batch completed: {res.get('curated_count', 0)} learner drops synchronized.")
            except Exception as e:
                print(f"[autonomous-worker] Maintenance loop notice: {e}")
            await asyncio.sleep(86400)  # Run once every 24 hours

    asyncio.create_task(_maintenance_loop())


