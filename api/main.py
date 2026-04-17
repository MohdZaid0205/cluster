from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from api.routers import users, clusters, posts, comments, triggers
from api.database import engine

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.models.cluster import ClusterBookmark
    from api.database import engine
    ClusterBookmark.__table__.create(engine, checkfirst=True)
    yield

app = FastAPI(title="Cluster API", version="1.0.0", description="Backend API for the Cluster application.", lifespan=lifespan)

# CORS – allow any client to connect for multi-user capabilities
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(clusters.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(triggers.router)

# ---------------------------------------------------------------------------
# Global Search endpoint — fans out across users, clusters, and post content
# ---------------------------------------------------------------------------
from sqlmodel import Session, select
from api.database import get_session
from api.models.user import UserProfile
from api.models.cluster import ClusterCore, ClusterInfo
from api.models.post import PostCore, PostContent, PostStats
from fastapi import Depends

@app.get("/search")
def global_search(q: str = "", limit: int = 15, session: Session = Depends(get_session)):
    """
    Global fuzzy search: tokenizes query and ORs ilike conditions across users, clusters, and posts.
    """
    from sqlalchemy import or_
    results: dict = {"users": [], "clusters": [], "posts": []}
    if not q.strip():
        return results

    # Tokenize: split on whitespace and punctuation, deduplicate
    tokens = list({t for t in q.strip().split() if len(t) > 0})

    # Users — match any token against name or bio
    user_conditions = [
        UserProfile.name.ilike(f"%{t}%")
        for t in tokens
    ]
    user_rows = session.exec(
        select(UserProfile).where(or_(*user_conditions)).limit(limit)
    ).all()
    results["users"] = [{"uid": str(u.uid), "name": u.name, "bio": u.bio} for u in user_rows]

    # Clusters — match any token against name, category, or tags
    cluster_conditions = []
    for t in tokens:
        cluster_conditions.append(ClusterCore.name.ilike(f"%{t}%"))
        cluster_conditions.append(ClusterCore.category.ilike(f"%{t}%"))
    cluster_rows = session.exec(
        select(ClusterCore, ClusterInfo)
        .join(ClusterInfo, ClusterCore.cid == ClusterInfo.cid)
        .where(or_(*cluster_conditions))
        .limit(limit)
    ).all()
    results["clusters"] = [{"cid": str(c.cid), "name": c.name, "category": c.category} for c, _ in cluster_rows]

    # Posts — match any token in content or tags
    post_conditions = []
    for t in tokens:
        post_conditions.append(PostContent.content.ilike(f"%{t}%"))
        post_conditions.append(PostContent.tags.ilike(f"%{t}%"))
    post_rows = session.exec(
        select(PostCore, PostContent, PostStats, ClusterCore)
        .join(PostContent, PostCore.pid == PostContent.pid)
        .join(PostStats, PostCore.pid == PostStats.pid)
        .join(ClusterCore, PostCore.cid == ClusterCore.cid)
        .where(or_(*post_conditions))
        .order_by(PostStats.likes.desc())
        .limit(limit)
    ).all()
    results["posts"] = [
        {
            "pid": str(core.pid), "uid": str(core.uid), "cid": str(core.cid),
            "cluster_name": cluster.name,
            "content": content.content[:280], "tags": content.tags,
            "likes": stats.likes, "dislikes": stats.dislikes,
        }
        for core, content, stats, cluster in post_rows
    ]

    return results


# Mount the Static HTML/CSS/JS frontend application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "app", "web")
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return {"message": "Welcome to the Cluster API", "status": "ok", "ui_url": "/web"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
