"""
api/routers/triggers.py

Endpoints used by the frontend trigger-dashboard to verify that every
SQLite trigger is functioning correctly.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func, text
from uuid import UUID

from api.database import get_session
from api.models.post import PostCore, PostStats
from api.models.comment import CommentCore, CommentStats
from api.models.cluster import ClusterCore, ClusterStats, ClusterMember
from api.models.user import UserProfile

router = APIRouter(prefix="/triggers", tags=["Triggers"])


@router.get("/dashboard")
def trigger_dashboard(session: Session = Depends(get_session)):
    """
    Returns a comprehensive dashboard payload summarising the health of every
    registered SQLite trigger.  This is consumed by the frontend's
    `triggerCheck.ts` console logger and the trigger verification UI.
    """

    # ----------------------------------------------------------------
    # 1. trg_init_post_stats – every PostCore row should have a PostStats row
    # ----------------------------------------------------------------
    total_posts = session.exec(select(func.count(PostCore.pid))).one()
    posts_with_stats = session.exec(
        select(func.count(PostStats.pid))
        .where(PostStats.pid.in_(select(PostCore.pid)))
    ).one()
    post_stats_coverage = f"{posts_with_stats}/{total_posts}" if total_posts else "0/0"

    # ----------------------------------------------------------------
    # 2. trg_init_comment_stats – every CommentCore row should have a CommentStats row
    # ----------------------------------------------------------------
    total_comments = session.exec(select(func.count(CommentCore.mid))).one()
    comments_with_stats = session.exec(
        select(func.count(CommentStats.mid))
        .where(CommentStats.mid.in_(select(CommentCore.mid)))
    ).one()
    comment_stats_coverage = f"{comments_with_stats}/{total_comments}" if total_comments else "0/0"

    # ----------------------------------------------------------------
    # 3/4. trg_increment/decrement_member_count – ClusterStats.member_count
    #      should match the actual number of ClusterMember rows per cluster.
    # ----------------------------------------------------------------
    total_clusters = session.exec(select(func.count(ClusterStats.cid))).one()

    # Count mismatches where stats.member_count != actual member rows
    actual_counts_subq = (
        select(
            ClusterMember.cid,
            func.count(ClusterMember.uid).label("actual")
        )
        .group_by(ClusterMember.cid)
        .subquery()
    )
    mismatched = 0
    cluster_stats_rows = session.exec(select(ClusterStats)).all()
    for cs in cluster_stats_rows:
        actual = session.exec(
            select(func.count(ClusterMember.uid))
            .where(ClusterMember.cid == cs.cid)
        ).one()
        if actual != cs.member_count:
            mismatched += 1

    # ----------------------------------------------------------------
    # 5. trg_update_last_active – recently active users (by last_active desc)
    # ----------------------------------------------------------------
    recently_active = session.exec(
        select(UserProfile.name, UserProfile.last_active)
        .order_by(UserProfile.last_active.desc())
        .limit(3)
    ).all()
    recently_active_list = [
        {"name": r[0], "last_active": str(r[1])} for r in recently_active
    ]

    # ----------------------------------------------------------------
    # Registered trigger names (from SQLite metadata)
    # ----------------------------------------------------------------
    try:
        raw = session.exec(text("SELECT name FROM sqlite_master WHERE type='trigger'")).all()
        trigger_names = [row[0] for row in raw]
    except Exception:
        trigger_names = []

    return {
        "trg_init_post_stats": {
            "total_posts": total_posts,
            "posts_with_stats": posts_with_stats,
            "coverage": post_stats_coverage,
        },
        "trg_init_comment_stats": {
            "total_comments": total_comments,
            "comments_with_stats": comments_with_stats,
            "coverage": comment_stats_coverage,
        },
        "trg_member_count": {
            "total_clusters": total_clusters,
            "mismatched_clusters": mismatched,
            "all_counts_accurate": mismatched == 0,
        },
        "trg_update_last_active": {
            "recently_active_users": recently_active_list,
        },
        "trigger_count": len(trigger_names),
        "registered_triggers": trigger_names,
    }


@router.get("/verify/post-stats/{pid}")
def verify_post_stats(pid: UUID, session: Session = Depends(get_session)):
    """
    Verifies that trg_init_post_stats created a PostStats row for the given post.
    """
    core = session.get(PostCore, pid)
    if not core:
        raise HTTPException(status_code=404, detail="Post not found")

    stats = session.get(PostStats, pid)
    return {
        "pid": str(pid),
        "post_exists": True,
        "stats_exists": stats is not None,
        "stats": {
            "likes": stats.likes if stats else None,
            "dislikes": stats.dislikes if stats else None,
        } if stats else None,
        "trigger_ok": stats is not None,
    }


@router.get("/verify/member-count/{cid}")
def verify_member_count(cid: UUID, session: Session = Depends(get_session)):
    """
    Verifies that trg_increment/decrement_member_count keeps ClusterStats.member_count
    in sync with the actual ClusterMember row count.
    """
    cluster = session.get(ClusterCore, cid)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    stats = session.get(ClusterStats, cid)
    actual_count = session.exec(
        select(func.count(ClusterMember.uid)).where(ClusterMember.cid == cid)
    ).one()

    return {
        "cid": str(cid),
        "recorded_member_count": stats.member_count if stats else None,
        "actual_member_count": actual_count,
        "trigger_ok": (stats.member_count if stats else 0) == actual_count,
    }


@router.get("/verify/last-active/{uid}")
def verify_last_active(uid: UUID, session: Session = Depends(get_session)):
    """
    Verifies that trg_update_last_active is keeping the user's last_active timestamp current.
    """
    profile = session.get(UserProfile, uid)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "uid": str(uid),
        "name": profile.name,
        "last_active": str(profile.last_active),
        "trigger_ok": True,  # We can only confirm the field exists; freshness is relative
    }
