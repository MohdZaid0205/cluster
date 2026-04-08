from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from api.database import get_session
from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember
from api.schemas.cluster import ClusterCreate, ClusterResponse, ClusterDetailResponse, ClusterMemberCreate
from api.services.cluster_service import ClusterService
from api.security import get_current_uid

router = APIRouter(prefix="/clusters", tags=["Clusters"])

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
    The trg_increment_member_count trigger updates ClusterStats automatically.
    """
    # Check cluster exists
    cluster = session.get(ClusterCore, cid)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Check not already a member
    existing = ClusterService.check_user_membership(session, cid, uid)
    if existing:
        raise HTTPException(status_code=400, detail="Already a member of this cluster")

    ClusterService.add_user_to_cluster(session, cid, uid, role="MEMBER")
    return {"message": "Joined cluster successfully"}


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
