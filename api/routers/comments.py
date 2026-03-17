from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID

from api.database import get_session
from api.models.comment import CommentCore, CommentContent, CommentStats, CommentReaction
from api.schemas.comment import CommentCreate, CommentResponse, CommentReactionCreate
from api.services.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["Comments"])

@router.post("/", response_model=CommentResponse)
def create_comment(comment_in: CommentCreate, session: Session = Depends(get_session)):
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
