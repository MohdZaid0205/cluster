from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, desc
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime

from api.database import get_session
from api.models.post import (
    PostCore,
    PostContent,
    PostStats,
    PostReaction,
    Megaphone,
    Window,
    MegaphonePollOption,
    MegaphoneEventMeta,
)
from api.models.cluster import ClusterCore
from api.models.user import UserProfile
from api.schemas.post import PostCreate, PostResponse, PostReactionCreate
from api.services.post_service import PostService
from api.services.cluster_service import ClusterService
from api.services.megaphone_engagement_service import (
    get_poll_summary,
    get_event_summary,
    cast_poll_vote,
    set_event_rsvp,
)
from api.models.user import UserAuth
from api.models.enums import MegaphoneType, PostType, EventRsvpStatus
from api.auth import get_current_user, get_current_user_optional
from pydantic import BaseModel

router = APIRouter(prefix="/posts", tags=["Posts"])


def _serialize_post(core: PostCore, content: PostContent | None, stats: PostStats | None, session: Session = None) -> dict:
    """Convert a (PostCore, PostContent, PostStats) set to a JSON-serializable dict."""
    data = {
        "pid"       : str(core.pid),
        "uid"       : str(core.uid),
        "cid"       : str(core.cid),
        "type"      : core.type if isinstance(core.type, str) else core.type.value,
        "content"   : content.content if content else None,
        "tags"      : content.tags if content else None,
        "created_at": core.created_at.isoformat() if core.created_at else None,
        "likes"     : stats.likes if stats else 0,
        "dislikes"  : stats.dislikes if stats else 0,
        "megaphone" : None,
        "window_origin": None
    }

    if session:
        # Attach megaphone metadata if a Megaphone record exists for this post
        meg = session.get(Megaphone, core.pid)
        if meg:
            mt = meg.type.value if hasattr(meg.type, "value") else str(meg.type)
            cl = session.get(ClusterCore, core.cid)
            mdict: dict = {
                "start_time": meg.start_time.isoformat(),
                "end_time": meg.end_time.isoformat(),
                "type": mt,
                "is_active": meg.is_active,
                "subscriber_count": meg.subscriber_count,
                "cluster_cid": str(core.cid),
                "cluster_name": cl.name if cl else None,
            }
            if mt == "POLL":
                mdict["poll"] = get_poll_summary(session, core.pid, None)
            if mt == "EVENT":
                mdict["event"] = get_event_summary(session, core.pid, None)
            data["megaphone"] = mdict

        # Attach window metadata if this is a WINDOW type post
        is_window = (core.type == PostType.WINDOW) or (hasattr(core.type, "value") and core.type.value == "WINDOW") or (core.type == "WINDOW")
        if is_window:
            window = session.get(Window, core.pid)
            if window:
                origin_core = session.get(PostCore, window.origin_pid)
                if origin_core:
                    origin_content = session.get(PostContent, window.origin_pid)
                    cluster = session.get(ClusterCore, origin_core.cid)
                    author = session.exec(select(UserProfile).where(UserProfile.uid == origin_core.uid)).first()
                    
                    data["window_origin"] = {
                        "origin_pid": str(origin_core.pid),
                        "origin_cid": str(origin_core.cid),
                        "cluster_name": cluster.name if cluster else None,
                        "author_name": author.name if author else None,
                        "author_uid": str(origin_core.uid),
                        "content": origin_content.content if origin_content else None,
                        "created_at": origin_core.created_at.isoformat() if origin_core.created_at else None,
                    }

    return data


@router.post("/", response_model=PostResponse)
def create_post(post_in: PostCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Creates a new post. Only members of the cluster can create posts in it.
    """
    membership = ClusterService.check_user_membership(session, post_in.cid, current_user.uid)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this cluster to post in it."
        )

    core_post, content, stats = PostService.create_post(session, post_in)
    return _serialize_post(core_post, content, stats, session)


@router.get("/me/feed", response_model=List[Any])
def get_my_homepage_feed(limit: int = 50, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Generates a custom feed by extracting posts from clusters the user is a member of.
    """
    rows = PostService.get_homepage_feed_for_user(session, current_user.uid, limit)
    return [_serialize_post(core, content, stats, session) for core, content, stats in rows]


@router.get("/trending/global", response_model=List[Any])
def get_global_trending_posts(limit: int = 20, session: Session = Depends(get_session)):
    """
    Retrieves universally trending content across all public clusters based on like velocity.
    """
    rows = PostService.get_trending_posts_globally(session, limit)
    return [_serialize_post(core, content, stats, session) for core, content, stats in rows]


@router.get("/megaphones/active", response_model=List[Any])
def get_active_megaphones(session: Session = Depends(get_session)):
    """
    Fetches currently promoted global posts.
    """
    rows = PostService.get_active_megaphones(session)
    return [
        {"pid": str(pid), "content": content, "type": mtype.value if hasattr(mtype, "value") else mtype, "end_time": end_time.isoformat() if end_time else None}
        for pid, content, mtype, end_time in rows
    ]


@router.get("/{pid}", response_model=PostResponse)
def get_post(pid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves a single post by ID including its content and interaction stats.
    """
    result = PostService.get_post_full_details(session, pid)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")

    core, content, stats = result
    return _serialize_post(core, content, stats, session)


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
        response_list.append(_serialize_post(core, content, stats, session))
    return response_list


@router.post("/{pid}/react")
def react_to_post(pid: UUID, reaction_in: PostReactionCreate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Registers a user's reaction to a specific post.
    """
    result = PostService.add_reaction_to_post(session, pid, current_user.uid, reaction_in.reaction_type)
    return result


@router.delete("/{pid}")
def delete_post(pid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Deletes a post. Only the post author or a cluster moderator may delete it.
    """
    core = session.get(PostCore, pid)
    if not core:
        raise HTTPException(status_code=404, detail="Post not found")

    is_owner = str(core.uid) == str(current_user.uid)
    is_mod = ClusterService.is_cluster_moderator(session, core.cid, current_user.uid)
    if not is_owner and not is_mod:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be the post author or a cluster moderator to delete this post."
        )

    success = PostService.delete_post(session, pid)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted successfully"}


@router.delete("/{pid}/react")
def remove_reaction(pid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Removes the current user's reaction from a post.
    """
    result = PostService.remove_reaction_from_post(session, pid, current_user.uid)
    if not result:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return result


@router.get("/{pid}/reaction/me", response_model=Any)
def get_my_reaction(pid: UUID, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Returns the current user's reaction on a post, or null if none exists.
    """
    reaction = PostService.get_user_reaction_to_post(session, pid, current_user.uid)
    return {"reaction": reaction}


# ---- Post edit ---------------------------------------------------------------

class PostEditPayload(BaseModel):
    content: str
    tags: Optional[str] = None


@router.patch("/{pid}")
def edit_post(pid: UUID, payload: PostEditPayload, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Edits a post's content/tags. Only the original author may edit.
    """
    core = session.get(PostCore, pid)
    if not core:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(core.uid) != str(current_user.uid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the post author may edit this post.")

    content = session.get(PostContent, pid)
    if content:
        content.content = payload.content
        if payload.tags is not None:
            content.tags = payload.tags
        session.add(content)

    core.updated_at = datetime.now()
    session.add(core)
    session.commit()

    stats = session.get(PostStats, pid)
    return _serialize_post(core, content, stats)


# ---- Megaphone creation (moderator-only) ------------------------------------

class MegaphoneCreatePayload(BaseModel):
    cid: UUID
    content: str
    tags: Optional[str] = None
    megaphone_type: MegaphoneType = MegaphoneType.ANNOUNCEMENT
    duration_hours: int = 24
    poll_options: Optional[List[str]] = None
    event_starts_at: Optional[datetime] = None
    event_ends_at: Optional[datetime] = None
    event_location: Optional[str] = None


class PostSharePayload(BaseModel):
    target_cid: UUID


@router.post("/{pid}/share", response_model=PostResponse)
def share_post(
    pid: UUID,
    payload: PostSharePayload,
    session: Session = Depends(get_session),
    current_user: UserAuth = Depends(get_current_user)
):
    """
    Shares an existing post (pid) into a target cluster (target_cid).
    Creates a WINDOW-type post.
    """
    # Guard: must be a member of the target cluster
    membership = ClusterService.check_user_membership(session, payload.target_cid, current_user.uid)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a member of the target cluster to share a post into it.")

    core, content, stats = PostService.share_post_to_cluster(session, pid, payload.target_cid, current_user.uid)
    return _serialize_post(core, content, stats, session)


@router.post("/megaphone/create", response_model=Any)
def create_megaphone(
    payload: MegaphoneCreatePayload,
    session: Session = Depends(get_session),
    current_user: UserAuth = Depends(get_current_user)
):
    """
    Creates a megaphone (promoted announcement) post. Must be a moderator of the target cluster.
    """
    # Guard: must be a moderator of the target cluster
    is_mod = ClusterService.is_cluster_moderator(session, payload.cid, current_user.uid)
    membership = ClusterService.check_user_membership(session, payload.cid, current_user.uid)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this cluster.")
    if not is_mod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only cluster moderators can create megaphones.")

    poll_opts: List[str] = []
    if payload.megaphone_type == MegaphoneType.POLL:
        poll_opts = [o.strip() for o in (payload.poll_options or []) if o and str(o).strip()]
        if len(poll_opts) < 2 or len(poll_opts) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Poll megaphones require between 2 and 10 non-empty options.",
            )
    elif payload.poll_options:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="poll_options is only valid for POLL megaphones.")

    from api.schemas.post import PostCreate
    post_schema = PostCreate(
        uid=current_user.uid,
        cid=payload.cid,
        content=payload.content,
        tags=payload.tags,
        type="TEXT"
    )
    core_post, content, stats = PostService.create_post(session, post_schema)

    # Create the Megaphone promotion record
    now = datetime.now()
    meg = Megaphone(
        pid=core_post.pid,
        start_time=now,
        end_time=datetime(now.year, now.month, now.day, now.hour, now.minute, now.second) if payload.duration_hours == 0 else
                  datetime.fromtimestamp(now.timestamp() + payload.duration_hours * 3600),
        type=payload.megaphone_type,
        is_active=True,
        subscriber_count=0,
    )
    session.add(meg)
    if poll_opts:
        for i, label in enumerate(poll_opts):
            session.add(MegaphonePollOption(pid=core_post.pid, idx=i, label=label))
    if payload.megaphone_type == MegaphoneType.EVENT:
        if payload.event_starts_at or payload.event_ends_at or (payload.event_location and payload.event_location.strip()):
            session.add(
                MegaphoneEventMeta(
                    pid=core_post.pid,
                    starts_at=payload.event_starts_at,
                    ends_at=payload.event_ends_at,
                    location=payload.event_location.strip() if payload.event_location else None,
                )
            )
    session.commit()

    return _serialize_post(core_post, content, stats, session)


@router.get("/cluster/{cid}/recent", response_model=List[Any])
def get_recent_cluster_posts(cid: UUID, limit: int = 50, session: Session = Depends(get_session)):
    """
    Feed generator for a specific cluster container.
    """
    rows = PostService.get_recent_posts_for_cluster(session, cid, limit)
    return [{"pid": str(pid), "content": content, "likes": likes, "created_at": ca.isoformat() if ca else None}
            for pid, content, likes, ca in rows]


@router.get("/user/{uid}/recent", response_model=List[Any])
def get_recent_user_posts(uid: UUID, limit: int = 50, session: Session = Depends(get_session)):
    """
    Feed generator for a specific user's public profile.
    """
    rows = PostService.get_recent_posts_by_user(session, uid, limit)
    return [{"pid": str(pid), "content": content, "likes": likes, "created_at": ca.isoformat() if ca else None}
            for pid, content, likes, ca in rows]


@router.get("/cluster/{cid}/top-liked", response_model=List[Any])
def get_top_liked_posts_in_cluster(cid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    return PostService.get_top_liked_posts_in_cluster(session, cid, limit)


@router.get("/cluster/{cid}/controversial", response_model=List[Any])
def get_most_controversial_posts_in_cluster(cid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    return PostService.get_most_controversial_posts_in_cluster(session, cid, limit)


@router.get("/{pid}/likes", response_model=List[Any])
def list_post_likers(pid: UUID, session: Session = Depends(get_session)):
    return PostService.list_users_who_liked_post(session, pid)


@router.get("/{pid}/reactions/stats", response_model=List[Any])
def get_post_reaction_stats(pid: UUID, session: Session = Depends(get_session)):
    rows = PostService.count_post_reactions_by_type(session, pid)
    out = []
    for row in rows:
        rt = row[0]
        cnt = row[1]
        name = getattr(rt, "name", None) or getattr(rt, "value", None) or str(rt)
        if isinstance(name, str) and "." in name:
            name = name.split(".")[-1]
        out.append({"reaction_type": name, "count": int(cnt)})
    return out


@router.get("/{pid}/windows", response_model=List[Any])
def get_post_windows(pid: UUID, session: Session = Depends(get_session)):
    return PostService.get_windows_for_post(session, pid)


@router.get("/{pid}/window-origin", response_model=Any)
def get_window_origin(pid: UUID, session: Session = Depends(get_session)):
    """
    For a WINDOW-type post identified by pid, returns the original post data
    (content, cluster name, author name) so the UI can show "Originally posted in..."
    """
    from api.models.post import Window
    from api.models.cluster import ClusterCore, ClusterInfo
    from api.models.user import UserProfile

    window = session.get(Window, pid)
    if not window:
        raise HTTPException(status_code=404, detail="No window record for this post")

    origin_core = session.get(PostCore, window.origin_pid)
    if not origin_core:
        raise HTTPException(status_code=404, detail="Original post not found")

    origin_content = session.get(PostContent, window.origin_pid)
    origin_stats = session.get(PostStats, window.origin_pid)

    # Resolve cluster name
    cluster = session.get(ClusterCore, origin_core.cid)
    cluster_info_stmt = select(ClusterInfo).where(ClusterInfo.cid == origin_core.cid)
    cluster_info = session.exec(cluster_info_stmt).first()

    # Resolve author name
    author = session.exec(select(UserProfile).where(UserProfile.uid == origin_core.uid)).first()

    return {
        "origin_pid": str(origin_core.pid),
        "origin_cid": str(origin_core.cid),
        "cluster_name": cluster.name if cluster else None,
        "author_name": author.name if author else None,
        "author_uid": str(origin_core.uid),
        "content": origin_content.content if origin_content else None,
        "tags": origin_content.tags if origin_content else None,
        "created_at": origin_core.created_at.isoformat() if origin_core.created_at else None,
        "likes": origin_stats.likes if origin_stats else 0,
        "dislikes": origin_stats.dislikes if origin_stats else 0,
    }


@router.get("/{pid}/megaphone-info", response_model=Any)
def get_megaphone_info(pid: UUID, session: Session = Depends(get_session)):
    """
    Returns megaphone metadata for a promoted post (cluster, schedule, poll/event summaries).
    """
    meg = session.get(Megaphone, pid)
    if not meg:
        raise HTTPException(status_code=404, detail="No megaphone record for this post")
    core = session.get(PostCore, pid)
    cl = session.get(ClusterCore, core.cid) if core else None
    mt = meg.type.value if hasattr(meg.type, "value") else str(meg.type)
    out: dict = {
        "pid": str(pid),
        "start_time": meg.start_time.isoformat(),
        "end_time": meg.end_time.isoformat(),
        "type": mt,
        "is_active": meg.is_active,
        "subscriber_count": meg.subscriber_count,
        "cluster_cid": str(core.cid) if core else None,
        "cluster_name": cl.name if cl else None,
    }
    if mt == "POLL":
        out["poll"] = get_poll_summary(session, pid, None)
    if mt == "EVENT":
        out["event"] = get_event_summary(session, pid, None)
    return out


class PollVotePayload(BaseModel):
    option_index: int


class EventRsvpPayload(BaseModel):
    status: str


@router.get("/{pid}/megaphone/engagement", response_model=Any)
def get_megaphone_engagement(
    pid: UUID,
    session: Session = Depends(get_session),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
):
    """
    Live megaphone engagement: poll counts and per-user vote, or event RSVP totals and mine.
    Poll periodically from the client for real-time updates.
    """
    meg = session.get(Megaphone, pid)
    if not meg:
        raise HTTPException(status_code=404, detail="No megaphone record for this post")
    uid = current_user.uid if current_user else None
    core = session.get(PostCore, pid)
    cl = session.get(ClusterCore, core.cid) if core else None
    mt = meg.type.value if hasattr(meg.type, "value") else str(meg.type)
    out: dict = {
        "pid": str(pid),
        "start_time": meg.start_time.isoformat(),
        "end_time": meg.end_time.isoformat(),
        "type": mt,
        "is_active": meg.is_active,
        "subscriber_count": meg.subscriber_count,
        "cluster_cid": str(core.cid) if core else None,
        "cluster_name": cl.name if cl else None,
    }
    if mt == "POLL":
        out["poll"] = get_poll_summary(session, pid, uid)
    if mt == "EVENT":
        out["event"] = get_event_summary(session, pid, uid)
    return out


@router.post("/{pid}/megaphone/poll/vote", response_model=Any)
def vote_megaphone_poll(
    pid: UUID,
    body: PollVotePayload,
    session: Session = Depends(get_session),
    current_user: UserAuth = Depends(get_current_user),
):
    try:
        return cast_poll_vote(session, pid, current_user.uid, body.option_index)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{pid}/megaphone/event/rsvp", response_model=Any)
def rsvp_megaphone_event(
    pid: UUID,
    body: EventRsvpPayload,
    session: Session = Depends(get_session),
    current_user: UserAuth = Depends(get_current_user),
):
    try:
        st = body.status.strip().upper()
        if st not in ("GOING", "MAYBE", "NOT_GOING"):
            raise ValueError("status must be GOING, MAYBE, or NOT_GOING")
        return set_event_rsvp(session, pid, current_user.uid, EventRsvpStatus(st))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
