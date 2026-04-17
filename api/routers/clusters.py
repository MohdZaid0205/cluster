from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from api.database import get_session
from api.models.cluster import (
    ClusterCore,
    ClusterInfo,
    ClusterStats,
    ClusterMember,
    ClusterBookmark,
    ClusterChatOption,
)
from api.schemas.cluster import ClusterCreate, ClusterResponse, ClusterDetailResponse, ClusterMemberCreate
from api.services.cluster_service import ClusterService
from api.security import get_current_uid

router = APIRouter(prefix="/clusters", tags=["Clusters"])


class ClusterChatOptionUpdate(BaseModel):
    chat_enabled: bool

@router.post("/", response_model=ClusterDetailResponse)
def create_cluster(cluster_in: ClusterCreate, session: Session = Depends(get_session)):
    """
    Creates a new cluster instance, including its core schema, info, stats, and initial member assignment.
    """
    core_cluster, info, stats = ClusterService.create_cluster(session, cluster_in)

    return {
        "cid"         : core_cluster.cid,
        "name"        : core_cluster.name,
        "category"    : core_cluster.category,
        "is_private"  : core_cluster.is_private,
        "profile_icon": core_cluster.profile_icon,
        "description" : info.description,
        "creator_uid" : info.creator_uid,
        "tags"        : info.tags,
        "created_at"  : info.created_at,
        "member_count": stats.member_count
    }


@router.get("/memberships/me")
def get_my_cluster_memberships(
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Returns all cluster IDs the authenticated user has joined.
    """
    statement = select(ClusterMember.cid).where(ClusterMember.uid == uid)
    cids = session.exec(statement).all()
    return {"cluster_ids": [str(cid) for cid in cids]}


@router.post("/{cid}/bookmark")
def bookmark_cluster(
    cid: UUID,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Bookmarks a cluster for the authenticated user.
    Idempotent — returns success even if already bookmarked.
    """
    cluster = session.get(ClusterCore, cid)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    existing = session.exec(
        select(ClusterBookmark).where(ClusterBookmark.cid == cid, ClusterBookmark.uid == uid)
    ).first()
    if existing:
        return {"message": "Already bookmarked", "already_bookmarked": True}

    bookmark = ClusterBookmark(cid=cid, uid=uid)
    session.add(bookmark)
    session.commit()
    return {"message": "Cluster bookmarked", "already_bookmarked": False}


@router.delete("/{cid}/bookmark")
def unbookmark_cluster(
    cid: UUID,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Removes a bookmark for the authenticated user.
    Idempotent — returns success if no bookmark exists.
    """
    bookmark = session.exec(
        select(ClusterBookmark).where(ClusterBookmark.cid == cid, ClusterBookmark.uid == uid)
    ).first()
    if not bookmark:
        return {"message": "Bookmark not found", "already_removed": True}

    session.delete(bookmark)
    session.commit()
    return {"message": "Cluster unbookmarked", "already_removed": False}


@router.get("/bookmarks/me")
def get_my_bookmarked_clusters(
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Returns bookmarked clusters with chat option and membership status.
    """
    bookmarks = session.exec(
        select(ClusterBookmark)
        .where(ClusterBookmark.uid == uid)
        .order_by(ClusterBookmark.bookmarked_at.desc())
    ).all()

    response = []
    for bookmark in bookmarks:
        cluster = session.get(ClusterCore, bookmark.cid)
        if not cluster:
            continue

        chat_option = session.exec(
            select(ClusterChatOption).where(ClusterChatOption.cid == bookmark.cid, ClusterChatOption.uid == uid)
        ).first()
        membership = session.exec(
            select(ClusterMember).where(ClusterMember.cid == bookmark.cid, ClusterMember.uid == uid)
        ).first()

        response.append(
            {
                "cid": str(cluster.cid),
                "name": cluster.name,
                "category": cluster.category,
                "bookmarked_at": bookmark.bookmarked_at,
                "chat_enabled": chat_option.chat_enabled if chat_option else True,
                "is_member": membership is not None,
            }
        )

    return response


@router.put("/{cid}/chat-options")
def update_cluster_chat_options(
    cid: UUID,
    payload: ClusterChatOptionUpdate,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Updates authenticated user's chat option for a cluster.
    """
    cluster = session.get(ClusterCore, cid)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    option = session.exec(
        select(ClusterChatOption).where(ClusterChatOption.cid == cid, ClusterChatOption.uid == uid)
    ).first()

    if not option:
        option = ClusterChatOption(
            cid=cid,
            uid=uid,
            chat_enabled=payload.chat_enabled,
            updated_at=datetime.now(UTC),
        )
        session.add(option)
    else:
        option.chat_enabled = payload.chat_enabled
        option.updated_at = datetime.now(UTC)

    session.commit()

    return {
        "cid": str(cid),
        "chat_enabled": option.chat_enabled,
        "updated_at": option.updated_at,
    }


@router.get("/chat-options/me")
def get_my_chat_options(
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Returns chat options configured by the authenticated user.
    """
    options = session.exec(select(ClusterChatOption).where(ClusterChatOption.uid == uid)).all()
    response = []
    for option in options:
        cluster = session.get(ClusterCore, option.cid)
        response.append(
            {
                "cid": str(option.cid),
                "name": cluster.name if cluster else None,
                "category": cluster.category if cluster else None,
                "chat_enabled": option.chat_enabled,
                "updated_at": option.updated_at,
            }
        )
    return response

@router.get("/{cid}", response_model=ClusterDetailResponse)
def get_cluster(cid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves full details for a specified cluster including its extended info and stats.
    """
    result = ClusterService.get_cluster_full_profile(session, cid)
    if not result:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    core, info, stats = result

    return {
        "cid"         : core.cid,
        "name"        : core.name,
        "category"    : core.category,
        "is_private"  : core.is_private,
        "profile_icon": core.profile_icon,
        "description" : info.description if info else None,
        "creator_uid" : info.creator_uid if info else None,
        "created_at"  : info.created_at if info else None,
        "tags"        : info.tags if info else None,
        "member_count": stats.member_count if stats else 0
    }

@router.get("/", response_model=List[ClusterResponse])
def list_clusters(skip: int = 0, limit: int = 100, category: str = None, session: Session = Depends(get_session)):
    """
    Retrieves a paginated list of all active clusters in the system, optionally filtered by category.
    """
    statement = select(ClusterCore)
    if category:
        statement = statement.where(ClusterCore.category == category)
    
    statement = statement.offset(skip).limit(limit)
    clusters = session.exec(statement).all()
    return clusters

# ---- Membership endpoints (auth required) -----------------------------------

@router.post("/{cid}/join")
def join_cluster(
    cid: UUID,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Adds the authenticated user as a member of the specified cluster.
    Idempotent — returns success even if already a member.
    """
    cluster = session.get(ClusterCore, cid)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    _member, created = ClusterService.add_user_to_cluster(
        session,
        cid,
        uid,
        role="MEMBER",
        return_created=True,
    )
    if created:
        return {"message": "Joined cluster successfully", "already_member": False}
    return {"message": "Already a member of this cluster", "already_member": True}


@router.delete("/{cid}/leave")
def leave_cluster(
    cid: UUID,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Removes the authenticated user from the specified cluster.
    The trg_decrement_member_count trigger updates ClusterStats automatically.
    """
    removed = ClusterService.remove_user_from_cluster(session, cid, uid)
    if not removed:
        raise HTTPException(status_code=404, detail="Membership not found")
    return {"message": "Left cluster successfully"}
