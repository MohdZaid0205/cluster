from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from api.routers import users, clusters, posts, comments, triggers
from api.database import engine

# Make sure all models are imported so SQLModel knows about them (only needed if we create tables here, but we are connecting to existing)
# from api.models.user import UserAuth
# from sqlmodel import SQLModel

app = FastAPI(title="Cluster API", version="1.0.0", description="Backend API for the Cluster application.")

# CORS – allow any client to connect for multi-user capabilities
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # changed from localhost specifically to asterisk to allow everyone on your IP address to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: We do not call SQLModel.metadata.create_all(engine) because the database
# already exists and is populated via `archive/research/populate.py`. 
# We are just connecting to existing `temp/db/research.db`!

app.include_router(users.router)
app.include_router(clusters.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(triggers.router)

# Mount the Static HTML/CSS/JS frontend application
# Base directory is one level up from "api" (where "app" is located)
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
