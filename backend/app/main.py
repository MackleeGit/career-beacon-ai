import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import test, onboarding, recommendations
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(test.router)
app.include_router(onboarding.router)
app.include_router(recommendations.router)

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
