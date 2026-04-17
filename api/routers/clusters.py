from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Any, Optional
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
from api.models.user import UserAuth
from api.auth import get_current_user

router = APIRouter(prefix="/clusters", tags=["Clusters"])


class ClusterChatOptionUpdate(BaseModel):
    chat_enabled: bool

@router.post("/", response_model=ClusterDetailResponse)
def create_cluster(cluster_in: ClusterCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
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

@router.delete("/{cid}")
def delete_cluster(cid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Deletes a cluster. Validates if it was deleted successfully.
    """
    # Note: In a real system, verify current_user is creator/admin.
    success = ClusterService.delete_cluster(session, cid)
    if not success:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return {"message": "Cluster deleted successfully"}

@router.post("/{cid}/join")
def join_cluster(cid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Allows the authenticated user to join a cluster.
    """
    # Check if already a member
    if ClusterService.check_user_membership(session, cid, current_user.uid):
        raise HTTPException(status_code=400, detail="User already in cluster")
    ClusterService.add_user_to_cluster(session, cid, current_user.uid)
    return {"message": "Joined cluster successfully"}

@router.delete("/{cid}/leave")
def leave_cluster(cid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Allows the authenticated user to leave a cluster.
    """
    success = ClusterService.remove_user_from_cluster(session, cid, current_user.uid)
    if not success:
        raise HTTPException(status_code=404, detail="Not a member of this cluster")
    return {"message": "Left cluster successfully"}

@router.get("/public/popular", response_model=List[Any])
def get_popular_public_clusters(limit: int = 10, session: Session = Depends(get_session)):
    """
    Lists public clusters sorted by their member count.
    """
    return ClusterService.get_public_clusters_by_popularity(session, limit)

@router.get("/search/{query_term}", response_model=List[ClusterResponse])
def search_clusters(query_term: str, session: Session = Depends(get_session)):
    """
    Retrieves clusters matching a specific name pattern.
    """
    return ClusterService.search_clusters_by_name(session, query_term)

@router.get("/category/{category}", response_model=List[Any])
def get_clusters_by_category(category: str, limit: int = 10, session: Session = Depends(get_session)):
    """
    Fetches clusters within a target category, sorted by member count.
    """
    return ClusterService.get_clusters_by_category(session, category, limit)

@router.get("/{cid}/rules", response_model=List[Any])
def list_cluster_rules(cid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves moderation pattern rules configured for a cluster.
    """
    return ClusterService.list_cluster_rules(session, cid)

@router.get("/{cid}/creator", response_model=Any)
def get_cluster_creator(cid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves public information about the user who created this cluster.
    """
    result = ClusterService.get_cluster_creator_profile(session, cid)
    if not result:
        raise HTTPException(status_code=404, detail="Creator not found")
    return result

@router.get("/{cid}/moderators", response_model=List[Any])
def list_cluster_moderators(cid: UUID, session: Session = Depends(get_session)):
    """
    Lists all users holding explicitly assigned moderator roles in the cluster.
    """
    return ClusterService.list_cluster_moderators(session, cid)

@router.get("/{cid}/members", response_model=List[Any])
def list_cluster_members(cid: UUID, limit: int = 50, session: Session = Depends(get_session)):
    """
    Lists baseline membership representations.
    """
    return ClusterService.list_cluster_members(session, cid, limit)

@router.get("/stats/top-by-members", response_model=List[Any])
def get_top_clusters_by_members(limit: int = 5, session: Session = Depends(get_session)):
    """
    Analytical ranking of clusters by maximum population.
    """
    return ClusterService.get_top_clusters_by_members(session, limit)

@router.get("/stats/top-active", response_model=List[Any])
def get_top_active_clusters(limit: int = 5, session: Session = Depends(get_session)):
    """
    Analytical ranking of clusters by maximum content creation volume.
    """
    return ClusterService.get_top_active_clusters(session, limit)

@router.get("/stats/top-categories", response_model=List[Any])
def get_top_categories(limit: int = 5, session: Session = Depends(get_session)):
    """
    Analytical ranking of system categories by how many clusters represent them.
    """
    return ClusterService.get_top_categories(session, limit)

@router.get("/me/recommendations", response_model=List[Any])
def get_cluster_recommendations(limit: int = 5, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Suggests new clusters for a user based on the categories of clusters they already joined.
    """
    return ClusterService.get_cluster_recommendations_for_user(session, current_user.uid, limit)
