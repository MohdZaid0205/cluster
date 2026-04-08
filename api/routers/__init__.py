# =====================================================================
# API Routers Module
# =====================================================================
# This package exposes all the FastAPI routers used in the application.
# By consolidating all router imports in this module, the main application
# file can effortlessly hook them up. The routers handle the HTTP endpoints
# for users, clusters, posts, comments, and trigger verification.
# =====================================================================

from .users import router as users_router
from .clusters import router as clusters_router
from .posts import router as posts_router
from .comments import router as comments_router
from .triggers import router as triggers_router

__all__ = ["users_router", "clusters_router", "posts_router", "comments_router", "triggers_router"]
