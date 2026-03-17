from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID

from api.database import get_session
from api.models.post import PostCore, PostContent, PostStats, PostReaction
from api.schemas.post import PostCreate, PostResponse, PostReactionCreate
from api.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostResponse)
def create_post(post_in: PostCreate, session: Session = Depends(get_session)):
    """
    Creates a new post, initializing its core entity, text content, and interaction statistics.
    """
    core_post, content, stats = PostService.create_post(session, post_in)

    return {
        "pid"       : core_post.pid,
        "uid"       : core_post.uid,
        "cid"       : core_post.cid,
        "type"      : core_post.type,
        "content"   : content.content,
        "tags"      : content.tags,
        "created_at": core_post.created_at,
        "likes"     : stats.likes,
        "dislikes"  : stats.dislikes
    }

@router.get("/{pid}", response_model=PostResponse)
def get_post(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves a single post by ID including its content and interaction stats.
    """
    result = PostService.get_post_full_details(session, pid)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
        
    core, content, stats = result

    return {
        "pid"       : core.pid,
        "uid"       : core.uid,
        "cid"       : core.cid,
        "type"      : core.type,
        "content"   : content.content if content else None,
        "tags"      : content.tags if content else None,
        "created_at": core.created_at,
        "likes"     : stats.likes if stats else 0,
        "dislikes"  : stats.dislikes if stats else 0
    }

@router.get("/", response_model=List[PostResponse])
def list_posts(skip: int = 0, limit: int = 100, cid: Optional[UUID] = None, session: Session = Depends(get_session)):
    """
    Fetches a paginated list of posts, optionally filtered by a specific cluster ID.
    """
    statement = select(PostCore)
    if cid:
        statement = statement.where(PostCore.cid == cid)
    
    statement = statement.offset(skip).limit(limit)
    posts_core = session.exec(statement).all()
    
    response_list = []
    for core in posts_core:
        content = session.get(PostContent, core.pid)
        stats = session.get(PostStats, core.pid)
        response_list.append({
            "pid"       : core.pid,
            "uid"       : core.uid,
            "cid"       : core.cid,
            "type"      : core.type,
            "content"   : content.content if content else None,
            "tags"      : content.tags if content else None,
            "created_at": core.created_at,
            "likes"     : stats.likes if stats else 0,
            "dislikes"  : stats.dislikes if stats else 0
        })
    return response_list

@router.post("/{pid}/react")
def react_to_post(pid: UUID, reaction_in: PostReactionCreate, session: Session = Depends(get_session)):
    """
    Registers a user's reaction to a specific post.
    """
    PostService.add_reaction_to_post(session, pid, reaction_in.uid, reaction_in.reaction_type)
    return {"message": "Reaction recorded successfully"}
