from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select, col

from api.models.enums import MegaphoneType, EventRsvpStatus
from api.models.post import (
    Megaphone,
    MegaphonePollOption,
    MegaphonePollVote,
    MegaphoneEventMeta,
    MegaphoneEventRsvp,
    PostCore,
)
from api.services.cluster_service import ClusterService


def megaphone_is_live(meg: Megaphone) -> bool:
    if not meg.is_active:
        return False
    return meg.end_time > datetime.now()


def get_poll_summary(session: Session, pid: UUID, uid: Optional[UUID]) -> dict[str, Any]:
    opts = session.exec(
        select(MegaphonePollOption).where(MegaphonePollOption.pid == pid).order_by(col(MegaphonePollOption.idx))
    ).all()
    votes = session.exec(select(MegaphonePollVote).where(MegaphonePollVote.pid == pid)).all()
    counts: dict[int, int] = {o.idx: 0 for o in opts}
    for v in votes:
        counts[v.option_idx] = counts.get(v.option_idx, 0) + 1
    total = len(votes)
    my_vote: Optional[int] = None
    if uid:
        row = session.exec(
            select(MegaphonePollVote).where(MegaphonePollVote.pid == pid, MegaphonePollVote.uid == uid)
        ).first()
        if row:
            my_vote = row.option_idx
    return {
        "options": [{"idx": o.idx, "label": o.label, "votes": counts.get(o.idx, 0)} for o in opts],
        "total_votes": total,
        "my_vote": my_vote,
    }


def _rsvp_status_str(status: Any) -> str:
    s = status
    v = s.value if hasattr(s, "value") else str(s)
    return v.split(".")[-1] if "." in v else v  # guard if repr ever differs


def get_event_summary(session: Session, pid: UUID, uid: Optional[UUID]) -> dict[str, Any]:
    meta = session.get(MegaphoneEventMeta, pid)
    rsvps = session.exec(select(MegaphoneEventRsvp).where(MegaphoneEventRsvp.pid == pid)).all()
    going = sum(1 for r in rsvps if _rsvp_status_str(r.status) == EventRsvpStatus.GOING.value)
    maybe = sum(1 for r in rsvps if _rsvp_status_str(r.status) == EventRsvpStatus.MAYBE.value)
    not_going = sum(1 for r in rsvps if _rsvp_status_str(r.status) == EventRsvpStatus.NOT_GOING.value)
    total = len(rsvps)
    my_status: Optional[str] = None
    if uid:
        row = session.exec(
            select(MegaphoneEventRsvp).where(MegaphoneEventRsvp.pid == pid, MegaphoneEventRsvp.uid == uid)
        ).first()
        if row:
            my_status = _rsvp_status_str(row.status)
    return {
        "starts_at": meta.starts_at.isoformat() if meta and meta.starts_at else None,
        "ends_at": meta.ends_at.isoformat() if meta and meta.ends_at else None,
        "location": meta.location if meta else None,
        "counts": {"GOING": going, "MAYBE": maybe, "NOT_GOING": not_going, "total_rsvps": total},
        "my_status": my_status,
    }


def _meg_type_str(m: Megaphone) -> str:
    t = m.type
    return t.value if hasattr(t, "value") else str(t)


def cast_poll_vote(
    session: Session, pid: UUID, uid: UUID, option_idx: int
) -> dict[str, Any]:
    meg = session.get(Megaphone, pid)
    if not meg or _meg_type_str(meg) != MegaphoneType.POLL.value:
        raise ValueError("Not a poll megaphone")
    if not megaphone_is_live(meg):
        raise ValueError("This megaphone is no longer active")
    opt = session.exec(
        select(MegaphonePollOption).where(
            MegaphonePollOption.pid == pid, MegaphonePollOption.idx == option_idx
        )
    ).first()
    if not opt:
        raise ValueError("Invalid poll option")
    core = session.get(PostCore, pid)
    if not core:
        raise ValueError("Post not found")
    if not ClusterService.check_user_membership(session, core.cid, uid):
        raise ValueError("Only cluster members can vote")

    existing = session.exec(
        select(MegaphonePollVote).where(MegaphonePollVote.pid == pid, MegaphonePollVote.uid == uid)
    ).first()
    if existing:
        existing.option_idx = option_idx
        session.add(existing)
    else:
        session.add(MegaphonePollVote(pid=pid, uid=uid, option_idx=option_idx))
    session.commit()
    return get_poll_summary(session, pid, uid)


def set_event_rsvp(
    session: Session, pid: UUID, uid: UUID, status: EventRsvpStatus
) -> dict[str, Any]:
    meg = session.get(Megaphone, pid)
    if not meg or _meg_type_str(meg) != MegaphoneType.EVENT.value:
        raise ValueError("Not an event megaphone")
    if not megaphone_is_live(meg):
        raise ValueError("This megaphone is no longer active")
    core = session.get(PostCore, pid)
    if not core:
        raise ValueError("Post not found")
    if not ClusterService.check_user_membership(session, core.cid, uid):
        raise ValueError("Only cluster members can RSVP")

    row = session.exec(
        select(MegaphoneEventRsvp).where(MegaphoneEventRsvp.pid == pid, MegaphoneEventRsvp.uid == uid)
    ).first()
    if row:
        row.status = status
        row.updated_at = datetime.now()
        session.add(row)
    else:
        session.add(MegaphoneEventRsvp(pid=pid, uid=uid, status=status))
    session.commit()
    return get_event_summary(session, pid, uid)
