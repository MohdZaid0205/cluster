from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional, Any
from uuid import UUID

from api.database import get_session
from api.models.comment import CommentCore, CommentContent, CommentStats, CommentReaction
from api.schemas.comment import CommentCreate, CommentResponse, CommentReactionCreate
from api.services.comment_service import CommentService
from api.models.user import UserAuth
from api.auth import get_current_user

router = APIRouter(prefix="/comments", tags=["Comments"])

@router.post("/", response_model=CommentResponse)
def create_comment(comment_in: CommentCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Creates a new comment or reply, generating its core entity, text content, and interaction stats.
    """
    if not comment_in.pid and not comment_in.parent_mid:
        raise HTTPException(status_code=400, detail="Comment must belong to a post or another comment")

    core_comment, content, stats = CommentService.create_comment(session, comment_in)

    return {
        "mid"       : core_comment.mid,
        "uid"       : core_comment.uid,
        "pid"       : core_comment.pid,
        "parent_mid": core_comment.parent_mid,
        "content"   : content.content,
        "created_at": core_comment.created_at,
        "likes"     : stats.likes,
        "dislikes"  : stats.dislikes
    }

@router.get("/post/{pid}", response_model=List[CommentResponse])
def get_comments_for_post(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves a list of all comments associated with a specific post.
    """
    statement = select(CommentCore).where(CommentCore.pid == pid).order_by(CommentCore.created_at.desc())
    comments_core = session.exec(statement).all()
    
    response_list = []
    for core in comments_core:
        content = session.get(CommentContent, core.mid)
        stats = session.get(CommentStats, core.mid)
        response_list.append({
            "mid"       : core.mid,
            "uid"       : core.uid,
            "pid"       : core.pid,
            "parent_mid": core.parent_mid,
            "content"   : content.content if content else None,
            "created_at": core.created_at,
            "likes"     : stats.likes if stats else 0,
            "dislikes"  : stats.dislikes if stats else 0
        })
    return response_list

@router.delete("/{mid}")
def delete_comment(mid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Wipes a comment entity and cascade sweeps its descendants.
    """
    success = CommentService.delete_comment(session, mid)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Comment deleted successfully"}

@router.post("/{mid}/react")
def react_to_comment(mid: UUID, reaction_in: CommentReactionCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Appends or updates a user rating action on a specific comment.
    """
    CommentService.add_reaction_to_comment(session, mid, current_user.uid, reaction_in.reaction_type)
    return {"message": "Reaction recorded successfully"}

@router.get("/post/{pid}/root", response_model=List[Any])
def get_root_comments_for_post(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves top-level (direct) comments responding to a specific post.
    """
    return CommentService.get_root_comments_for_post(session, pid)

@router.get("/{parent_mid}/replies", response_model=List[Any])
def get_replies_for_comment(parent_mid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves all nested replies targeting a specific parent comment.
    """
    return CommentService.get_replies_for_comment(session, parent_mid)

@router.get("/post/{pid}/top", response_model=List[Any])
def get_top_comments_for_post(pid: UUID, limit: int = 10, session: Session = Depends(get_session)):
    """
    Algorithmically surfaces the most constructive (highest likes - dislikes ratio) comments.
    """
    return CommentService.get_top_comments_for_post(session, pid, limit)

@router.get("/{mid}/likes", response_model=List[Any])
def list_comment_likers(mid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves the profiles of users who left positive engagement on a comment.
    """
    return CommentService.list_users_who_liked_comment(session, mid)

@router.get("/{mid}/reaction/me", response_model=Any)
def check_my_reaction_to_comment(mid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Checks if the authenticated user reacted to a comment and retrieves the state.
    """
    result = CommentService.check_user_reaction_to_comment(session, mid, current_user.uid)
    if not result:
        return {"reaction_type": None}
    return {"reaction_type": result}
