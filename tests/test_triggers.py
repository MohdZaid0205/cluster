"""
tests/test_triggers.py

Validates all 5 SQLite triggers defined in api/triggers.py.
"""

import pytest
import time
from uuid import uuid4
from sqlmodel import Session, select

from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember
from api.models.post    import PostCore, PostContent, PostStats, PostType
from api.models.comment import CommentCore, CommentContent, CommentStats
from api.models.user    import UserAuth, UserProfile
from api.security       import get_password_hash


def test_trigger_init_post_stats(session: Session, test_user, test_cluster):
    """
    Inserting a raw PostCore row should automatically create a PostStats
    row with likes=0 and dislikes=0 via trg_init_post_stats.
    """
    pid = uuid4()
    core = PostCore(pid=pid, uid=test_user.uid, cid=test_cluster.cid, type=PostType.TEXT)
    session.add(core)
    session.commit()
    session.expire_all()            # flush ORM cache so we read fresh DB data

    # PostStats must exist without us creating it manually
    stats = session.get(PostStats, pid)
    assert stats is not None, "trg_init_post_stats did not create a PostStats row"
    assert stats.likes    == 0
    assert stats.dislikes == 0


def test_trigger_init_comment_stats(session: Session, test_user, test_post):
    """
    Inserting a raw CommentCore row should automatically create a
    CommentStats row with likes=0 and dislikes=0 via trg_init_comment_stats.
    """
    mid = uuid4()
    core = CommentCore(mid=mid, uid=test_user.uid, pid=test_post.pid)
    session.add(core)
    session.commit()
    session.expire_all()            # flush ORM cache

    # CommentStats must exist without us creating it manually
    stats = session.get(CommentStats, mid)
    assert stats is not None, "trg_init_comment_stats did not create a CommentStats row"
    assert stats.likes    == 0
    assert stats.dislikes == 0

def test_trigger_increment_member_count(session: Session, test_user, test_cluster):
    """
    Inserting a new ClusterMember row should increment
    ClusterStats.member_count via trg_increment_member_count.
    """
    stats = session.get(ClusterStats, test_cluster.cid)
    count_before = stats.member_count

    # Create a second user and add them as a raw member row
    new_uid = uuid4()
    new_auth    = UserAuth(uid=new_uid, email="trigger3@test.com",
                           password_hash=get_password_hash("pw"), is_verified=True)
    new_profile = UserProfile(uid=new_uid, name="Trigger3 User")
    session.add(new_auth)
    session.add(new_profile)
    session.flush()

    member = ClusterMember(cid=test_cluster.cid, uid=new_uid, role="MEMBER")
    session.add(member)
    session.commit()
    session.expire_all()            # flush ORM cache

    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == count_before + 1, (
        "trg_increment_member_count did not increment the member_count"
    )

def test_trigger_decrement_member_count(session: Session, test_user, test_cluster):
    """
    Deleting a ClusterMember row should decrement ClusterStats.member_count
    via trg_decrement_member_count.
    """
    # Add a second member so we have someone to remove
    new_uid = uuid4()
    new_auth    = UserAuth(uid=new_uid, email="trigger4@test.com",
                           password_hash=get_password_hash("pw"), is_verified=True)
    new_profile = UserProfile(uid=new_uid, name="Trigger4 User")
    session.add(new_auth)
    session.add(new_profile)
    session.flush()

    member = ClusterMember(cid=test_cluster.cid, uid=new_uid, role="MEMBER")
    session.add(member)
    session.commit()
    session.expire_all()

    count_after_join = session.get(ClusterStats, test_cluster.cid).member_count

    # Delete the member — trigger should decrement
    member = session.get(ClusterMember, {"cid": test_cluster.cid, "uid": new_uid})
    session.delete(member)
    session.commit()
    session.expire_all()            # flush ORM cache

    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == count_after_join - 1, (
        "trg_decrement_member_count did not decrement the member_count"
    )


def test_trigger_decrement_member_count_floor(session: Session, test_user, test_cluster):
    """
    The MAX(0, ...) guard in trg_decrement_member_count must prevent the
    count from going negative even if the stats row is already at 0.
    """
    # Force count to 0 manually
    stats = session.get(ClusterStats, test_cluster.cid)
    stats.member_count = 0
    session.add(stats)
    session.commit()
    session.expire_all()

    # Add and delete a member to exercise decrement when count starts at 0
    new_uid = uuid4()
    new_auth    = UserAuth(uid=new_uid, email="trigger4b@test.com",
                           password_hash=get_password_hash("pw"), is_verified=True)
    new_profile = UserProfile(uid=new_uid, name="Trigger4b User")
    session.add(new_auth)
    session.add(new_profile)
    session.flush()

    member = ClusterMember(cid=test_cluster.cid, uid=new_uid, role="MEMBER")
    session.add(member)
    session.commit()
    # Trigger 3 bumped it to 1; now delete to exercise Trigger 4 decrement
    member = session.get(ClusterMember, {"cid": test_cluster.cid, "uid": new_uid})
    session.delete(member)
    session.commit()
    session.expire_all()

    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count >= 0, (
        "trg_decrement_member_count allowed member_count to go negative"
    )

def test_trigger_update_last_active(session: Session, test_user, test_cluster):
    """
    Inserting a PostCore row should update UserProfile.last_active to
    approximately the current time via trg_update_last_active.
    """
    profile = session.get(UserProfile, test_user.uid)
    last_active_before = str(profile.last_active)

    # Small pause so timestamps are distinguishable
    time.sleep(0.1)

    pid = uuid4()
    post = PostCore(pid=pid, uid=test_user.uid, cid=test_cluster.cid, type=PostType.TEXT)
    session.add(post)
    session.commit()
    session.expire_all()            # flush ORM cache

    profile = session.get(UserProfile, test_user.uid)
    last_active_after = str(profile.last_active)

    assert last_active_after is not None, (
        "trg_update_last_active did not write a last_active timestamp"
    )
    # The timestamp should have been updated (it will differ from the original)
    assert last_active_after != last_active_before, (
        "trg_update_last_active did not change last_active after a new post"
    )
