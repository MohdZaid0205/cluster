from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from sqlmodel import SQLModel

from api.routers import users, clusters, posts, comments, triggers
from api.database import engine
from api.triggers import apply_triggers_now

# Import all models so SQLModel.metadata knows about them
import api.models  # noqa: F401

app = FastAPI(title="Cluster API", version="1.0.0", description="Backend API for the Cluster application.")

# ---------------------------------------------------------------------------
# CORS – allow the Vite dev server (port 5173/8080) to talk to FastAPI (8000)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Create tables if they don't exist (safe for SQLite)
# ---------------------------------------------------------------------------
SQLModel.metadata.create_all(engine)

# Re-apply triggers now that tables definitely exist
try:
    apply_triggers_now(engine)
except Exception:
    pass  # triggers already registered via the connect event

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(users.router)
app.include_router(clusters.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(triggers.router)

# ---------------------------------------------------------------------------
# Static frontend (optional legacy HTML/CSS/JS UI)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "app", "web")
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return {"message": "Welcome to the Cluster API", "status": "ok", "ui_url": "/web"}
