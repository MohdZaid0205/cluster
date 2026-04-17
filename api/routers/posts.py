from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, desc
from typing import List, Optional, Any
from uuid import UUID

from api.database import get_session
from api.models.post import PostCore, PostContent, PostStats, PostReaction
from api.schemas.post import PostCreate, PostResponse, PostReactionCreate
from api.services.post_service import PostService
from api.models.user import UserAuth
from api.auth import get_current_user

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostResponse)
def create_post(post_in: PostCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
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
    
    statement = statement.order_by(desc(PostCore.created_at)).offset(skip).limit(limit)
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
def react_to_post(pid: UUID, reaction_in: PostReactionCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Registers a user's reaction to a specific post.
    """
    PostService.add_reaction_to_post(session, pid, current_user.uid, reaction_in.reaction_type)
    return {"message": "Reaction recorded successfully"}

@router.delete("/{pid}")
def delete_post(pid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Deletes a post completely from the system.
    """
    success = PostService.delete_post(session, pid)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted successfully"}

@router.delete("/{pid}/react")
def remove_reaction(pid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Removes the current user's reaction from a post.
    """
    success = PostService.remove_reaction_from_post(session, pid, current_user.uid)
    if not success:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return {"message": "Reaction removed successfully"}

@router.get("/me/feed", response_model=List[Any])
def get_my_homepage_feed(limit: int = 50, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Generates a custom feed by extracting posts only from clusters the user is a member of.
    """
    return PostService.get_homepage_feed_for_user(session, current_user.uid, limit)

@router.get("/trending/global", response_model=List[Any])
def get_global_trending_posts(limit: int = 20, session: Session = Depends(get_session)):
    """
    Retrieves universally trending content across all public clusters based on like velocity.
    """
    return PostService.get_trending_posts_globally(session, limit)

@router.get("/cluster/{cid}/recent", response_model=List[Any])
def get_recent_cluster_posts(cid: UUID, limit: int = 50, session: Session = Depends(get_session)):
    """
    Feed generator for a specific cluster container.
    """
    return PostService.get_recent_posts_for_cluster(session, cid, limit)

@router.get("/user/{uid}/recent", response_model=List[Any])
def get_recent_user_posts(uid: UUID, limit: int = 50, session: Session = Depends(get_session)):
    """
    Feed generator for a specific user's public profile.
    """
    return PostService.get_recent_posts_by_user(session, uid, limit)

@router.get("/cluster/{cid}/top-liked", response_model=List[Any])
def get_top_liked_posts_in_cluster(cid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Quality analytics finding the most lauded content in a cluster.
    """
    return PostService.get_top_liked_posts_in_cluster(session, cid, limit)

@router.get("/cluster/{cid}/controversial", response_model=List[Any])
def get_most_controversial_posts_in_cluster(cid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Analytics finding heavily downvoted content in a cluster.
    """
    return PostService.get_most_controversial_posts_in_cluster(session, cid, limit)

@router.get("/{pid}/likes", response_model=List[Any])
def list_post_likers(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves the profile names of users who engaged positively.
    """
    return PostService.list_users_who_liked_post(session, pid)

@router.get("/{pid}/reactions/stats", response_model=List[Any])
def get_post_reaction_stats(pid: UUID, session: Session = Depends(get_session)):
    """
    Aggregates reaction distributions for charting.
    """
    return PostService.count_post_reactions_by_type(session, pid)

@router.get("/megaphones/active", response_model=List[Any])
def get_active_megaphones(session: Session = Depends(get_session)):
    """
    Fetches currently promoted global posts.
    """
    return PostService.get_active_megaphones(session)

@router.get("/{pid}/windows", response_model=List[Any])
def get_post_windows(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves instances where a post has been embedded/shared elsewhere.
    """
    return PostService.get_windows_for_post(session, pid)
