from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Any, Optional
from uuid import UUID
from pydantic import BaseModel

from api.database import get_session
from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember, ClusterBookmark
from api.schemas.cluster import ClusterCreate, ClusterResponse, ClusterDetailResponse, ClusterMemberCreate
from api.services.cluster_service import ClusterService
from api.models.user import UserAuth
from api.auth import get_current_user

router = APIRouter(prefix="/clusters", tags=["Clusters"])


# ---- Pydantic bodies for new endpoints ------------------------------------

class ChatOptionPayload(BaseModel):
    chat_enabled: bool


# ---- Static-path endpoints (must be before /{cid} routes) -----------------

@router.get("/memberships/me", response_model=Any)
def get_my_memberships(session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Returns a list of cluster IDs the authenticated user has joined.
    """
    cluster_ids = ClusterService.get_user_joined_cluster_ids(session, current_user.uid)
    return {"cluster_ids": cluster_ids}

@router.get("/bookmarks/me", response_model=List[Any])
def get_my_bookmarks(session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Returns all clusters the authenticated user has bookmarked,
    enriched with membership status and chat preferences.
    """
    return ClusterService.get_user_bookmarked_clusters(session, current_user.uid)

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

@router.post("/{cid}/bookmark")
def bookmark_cluster(cid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Bookmarks a cluster for the authenticated user. Idempotent.
    """
    ClusterService.bookmark_cluster(session, current_user.uid, cid)
    return {"message": "Cluster bookmarked successfully"}

@router.delete("/{cid}/bookmark")
def unbookmark_cluster(cid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Removes a cluster bookmark for the authenticated user.
    """
    success = ClusterService.unbookmark_cluster(session, current_user.uid, cid)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed successfully"}

@router.put("/{cid}/chat-options")
def set_chat_option(cid: UUID, payload: ChatOptionPayload, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Updates the per-user chat preference for a bookmarked cluster.
    """
    result = ClusterService.set_cluster_chat_option(session, current_user.uid, cid, payload.chat_enabled)
    if not result:
        raise HTTPException(status_code=404, detail="Bookmark not found – bookmark the cluster first")
    return {"message": "Chat option updated", "chat_enabled": result.chat_enabled}

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
