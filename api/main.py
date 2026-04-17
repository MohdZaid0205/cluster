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

# CORS – allow any client to connect for multi-user capabilities
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # changed from localhost specifically to asterisk to allow everyone on your IP address to connect
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

if __name__ == "__main__":
    import uvicorn
    # Running on 0.0.0.0 allows connections from other users/devices on the same network
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
