import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import test, onboarding

app = FastAPI(
    title="Career Beacon AI Engine",
    description="AI-Powered Micro-Learning and Mentorship Backend API service",
    version="1.0.0"
)

# Configure CORS
IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"

app.add_middleware(
    CORSMiddleware,
    # In dev: allow all origins so any LAN IP / network works automatically.
    # In production: restrict to the explicit whitelist only.
    allow_origins=["*"] if IS_DEV else [
        "https://careerbeacon.netlify.app",  # Production (Netlify)
        "http://localhost:5173",             # Local development
        "http://127.0.0.1:5173",             # Local development (alternative)
    ],
    allow_credentials=not IS_DEV,  # credentials can't be used with wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(test.router)
app.include_router(onboarding.router)

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
