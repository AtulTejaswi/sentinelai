# SentinelAI — FastAPI Backend Entry Point
# Atul is responsible for this file and all imports below

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="SentinelAI",
    description="Behavioral Intelligence Platform for Campus Event Ecosystems",
    version="1.0.0"
)

from database import engine
import models

models.Base.metadata.create_all(bind=engine)


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route Imports ---
# Uncomment as each module is completed

from auth import router as auth_router
from users import router as users_router
from alerts import router as alerts_router
from analytics import router as analytics_router
from scoring import router as scoring_router

app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(scoring_router, prefix="/api/score", tags=["Scoring"])


@app.get("/")
def root():
    return {
        "service": "SentinelAI",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Stub routes (replace with real routers as work is completed) ---




