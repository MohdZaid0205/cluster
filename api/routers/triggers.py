"""
api/routers/triggers.py

Endpoints that demonstrate and verify the 5 SQL triggers in action.
Each endpoint queries the database to show the state that triggers maintain.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, text
from typing import Any, List
from uuid import UUID

from api.database import get_session

router = APIRouter(prefix="/triggers", tags=["Triggers"])


@router.get("/status", response_model=Any)
def get_trigger_status(session: Session = Depends(get_session)):
    """
    Lists all registered SQLite triggers and their SQL definitions.
    Shows which triggers are active in the database.
    """
    result = session.exec(
        text("SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name")
    ).all()
    return [{"name": row[0], "sql": row[1]} for row in result]


@router.get("/verify/post-stats/{pid}", response_model=Any)
def verify_post_stats_trigger(pid: UUID, session: Session = Depends(get_session)):
    """
    Trigger 1: trg_init_post_stats
    Verifies that after a post is inserted into `postcore`,
    a corresponding row was auto-created in `poststats` with likes=0, dislikes=0.
    """
    core = session.exec(
        text("SELECT pid, uid, created_at FROM postcore WHERE pid = :pid"), {"pid": str(pid)}
    ).first()
    if not core:
        return {"trigger": "trg_init_post_stats", "status": "error", "message": "Post not found"}

    stats = session.exec(
        text("SELECT pid, likes, dislikes FROM poststats WHERE pid = :pid"), {"pid": str(pid)}
    ).first()

    return {
        "trigger": "trg_init_post_stats",
        "description": "AFTER INSERT on postcore → auto-creates poststats row",
        "post_exists": True,
        "stats_auto_created": stats is not None,
        "stats": {"pid": stats[0], "likes": stats[1], "dislikes": stats[2]} if stats else None,
    }


@router.get("/verify/comment-stats/{mid}", response_model=Any)
def verify_comment_stats_trigger(mid: UUID, session: Session = Depends(get_session)):
    """
    Trigger 2: trg_init_comment_stats
    Verifies that after a comment is inserted into `commentcore`,
    a corresponding row was auto-created in `commentstats`.
    """
    core = session.exec(
        text("SELECT mid, uid, created_at FROM commentcore WHERE mid = :mid"), {"mid": str(mid)}
    ).first()
    if not core:
        return {"trigger": "trg_init_comment_stats", "status": "error", "message": "Comment not found"}

    stats = session.exec(
        text("SELECT mid, likes, dislikes FROM commentstats WHERE mid = :mid"), {"mid": str(mid)}
    ).first()

    return {
        "trigger": "trg_init_comment_stats",
        "description": "AFTER INSERT on commentcore → auto-creates commentstats row",
        "comment_exists": True,
        "stats_auto_created": stats is not None,
        "stats": {"mid": stats[0], "likes": stats[1], "dislikes": stats[2]} if stats else None,
    }


@router.get("/verify/member-count/{cid}", response_model=Any)
def verify_member_count_trigger(cid: UUID, session: Session = Depends(get_session)):
    """
    Triggers 3 & 4: trg_increment_member_count / trg_decrement_member_count
    Shows the actual member count from clustermember rows vs the trigger-maintained
    count in clusterstats. They should match.
    """
    actual_count = session.exec(
        text("SELECT COUNT(*) FROM clustermember WHERE cid = :cid"), {"cid": str(cid)}
    ).first()

    trigger_count = session.exec(
        text("SELECT member_count FROM clusterstats WHERE cid = :cid"), {"cid": str(cid)}
    ).first()

    cluster_name = session.exec(
        text("SELECT name FROM clustercore WHERE cid = :cid"), {"cid": str(cid)}
    ).first()

    return {
        "trigger": "trg_increment/decrement_member_count",
        "description": "AFTER INSERT/DELETE on clustermember → updates clusterstats.member_count",
        "cluster_name": cluster_name[0] if cluster_name else None,
        "actual_member_rows": actual_count[0] if actual_count else 0,
        "trigger_maintained_count": trigger_count[0] if trigger_count else 0,
        "counts_match": (actual_count[0] if actual_count else 0) == (trigger_count[0] if trigger_count else 0),
    }


@router.get("/verify/last-active/{uid}", response_model=Any)
def verify_last_active_trigger(uid: UUID, session: Session = Depends(get_session)):
    """
    Trigger 5: trg_update_last_active
    Shows the user's last_active timestamp from userprofile and their most
    recent post timestamp. The trigger keeps last_active in sync with posting.
    """
    profile = session.exec(
        text("SELECT name, last_active FROM userprofile WHERE uid = :uid"), {"uid": str(uid)}
    ).first()
    if not profile:
        return {"trigger": "trg_update_last_active", "status": "error", "message": "User not found"}

    latest_post = session.exec(
        text("SELECT created_at FROM postcore WHERE uid = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": str(uid)},
    ).first()

    return {
        "trigger": "trg_update_last_active",
        "description": "AFTER INSERT on postcore → updates userprofile.last_active",
        "user_name": profile[0],
        "last_active": profile[1],
        "latest_post_at": latest_post[0] if latest_post else None,
        "trigger_updated": latest_post is not None,
    }


@router.get("/dashboard", response_model=Any)
def trigger_dashboard(session: Session = Depends(get_session)):
    """
    Aggregate dashboard showing all 5 triggers and summary statistics
    proving they are active and working.
    """
    # 1. Count registered triggers
    triggers = session.exec(
        text("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name")
    ).all()
    trigger_names = [row[0] for row in triggers]

    # 2. Post stats coverage (trg_init_post_stats)
    total_posts = session.exec(text("SELECT COUNT(*) FROM postcore")).first()[0]
    posts_with_stats = session.exec(text("SELECT COUNT(*) FROM poststats")).first()[0]

    # 3. Comment stats coverage (trg_init_comment_stats)
    total_comments = session.exec(text("SELECT COUNT(*) FROM commentcore")).first()[0]
    comments_with_stats = session.exec(text("SELECT COUNT(*) FROM commentstats")).first()[0]

    # 4. Member count accuracy (trg_increment/decrement_member_count)
    # Check a sample of clusters
    mismatches = session.exec(text("""
        SELECT cs.cid, cs.member_count AS trigger_count, 
               (SELECT COUNT(*) FROM clustermember cm WHERE cm.cid = cs.cid) AS actual_count
        FROM clusterstats cs
        WHERE cs.member_count != (SELECT COUNT(*) FROM clustermember cm WHERE cm.cid = cs.cid)
        LIMIT 5
    """)).all()

    # 5. Total clusters
    total_clusters = session.exec(text("SELECT COUNT(*) FROM clustercore")).first()[0]

    # 6. Recent user activity (trg_update_last_active)
    recently_active = session.exec(text("""
        SELECT up.name, up.last_active 
        FROM userprofile up 
        ORDER BY up.last_active DESC 
        LIMIT 5
    """)).all()

    return {
        "registered_triggers": trigger_names,
        "trigger_count": len(trigger_names),
        "trg_init_post_stats": {
            "description": "AFTER INSERT on postcore → auto-creates poststats(pid, 0, 0)",
            "total_posts": total_posts,
            "posts_with_stats": posts_with_stats,
            "coverage": f"{(posts_with_stats/total_posts*100):.1f}%" if total_posts > 0 else "N/A",
        },
        "trg_init_comment_stats": {
            "description": "AFTER INSERT on commentcore → auto-creates commentstats(mid, 0, 0)",
            "total_comments": total_comments,
            "comments_with_stats": comments_with_stats,
            "coverage": f"{(comments_with_stats/total_comments*100):.1f}%" if total_comments > 0 else "N/A",
        },
        "trg_member_count": {
            "description": "AFTER INSERT/DELETE on clustermember → increments/decrements clusterstats.member_count",
            "total_clusters": total_clusters,
            "mismatched_clusters": len(mismatches),
            "all_counts_accurate": len(mismatches) == 0,
        },
        "trg_update_last_active": {
            "description": "AFTER INSERT on postcore → updates userprofile.last_active = CURRENT_TIMESTAMP",
            "recently_active_users": [{"name": r[0], "last_active": r[1]} for r in recently_active],
        },
    }
