import pytest
from uuid import uuid4
from sqlmodel import Session, select
from api.services.comment_service import CommentService
from api.models.comment import CommentCore, CommentContent, CommentStats, CommentReaction
from api.models.enums import ReactionType

@pytest.fixture(name="test_comment")
def test_comment_fixture(session: Session, test_user, test_post):
    class MockCommentIn:
        uid = test_user.uid
        pid = test_post.pid
        parent_mid = None
        content = "This is a test comment"
        
    core, content, stats = CommentService.create_comment(session, MockCommentIn())
    return core

def test_create_comment(session: Session, test_user, test_post):
    class MockCommentIn:
        uid = test_user.uid
        pid = test_post.pid
        parent_mid = None
        content = "My new comment"
        
    core, content, stats = CommentService.create_comment(session, MockCommentIn())
    
    assert core is not None
    assert core.pid == test_post.pid
    assert content.content == "My new comment"
    assert stats.likes == 0

def test_get_root_comments_for_post(session: Session, test_comment, test_post):
    comments = CommentService.get_root_comments_for_post(session, test_post.pid)
    assert len(comments) > 0
    assert comments[0].mid == test_comment.mid
    assert comments[0].content == "This is a test comment"

def test_create_reply_comment(session: Session, test_user, test_post, test_comment):
    class MockReplyIn:
        uid = test_user.uid
        pid = None # Optional for replies in some schemas, but let's keep it null to match commentcore schema defaults
        parent_mid = test_comment.mid
        content = "This is a reply"
        
    core, content, stats = CommentService.create_comment(session, MockReplyIn())
    
    assert core.parent_mid == test_comment.mid
    
    replies = CommentService.get_replies_for_comment(session, test_comment.mid)
    assert len(replies) > 0
    assert replies[0].mid == core.mid

def test_add_reaction_to_comment(session: Session, test_comment, test_user):
    reaction = CommentService.add_reaction_to_comment(session, test_comment.mid, test_user.uid, ReactionType.LIKE)
    assert reaction is not None
    
    stats = session.get(CommentStats, test_comment.mid)
    assert stats.likes == 1
    
    # Check "user liked this" list
    users_who_liked = CommentService.list_users_who_liked_comment(session, test_comment.mid)
    assert len(users_who_liked) > 0
    assert users_who_liked[0].name == "Test User"

def test_create_comment_rolls_back_when_content_insert_fails(session: Session, test_user, test_post, monkeypatch):
    class MockCommentIn:
        uid = test_user.uid
        pid = test_post.pid
        parent_mid = None
        content = "This comment should rollback"

    original_add = session.add

    def failing_add(obj):
        # Force a failure after CommentCore.flush() to verify rollback removes partial data.
        if isinstance(obj, CommentContent):
            raise RuntimeError("Simulated content insert failure")
        return original_add(obj)

    monkeypatch.setattr(session, "add", failing_add)

    with pytest.raises(RuntimeError):
        CommentService.create_comment(session, MockCommentIn())

    rows = session.exec(
        select(CommentCore).where(
            CommentCore.uid == test_user.uid,
            CommentCore.pid == test_post.pid,
        )
    ).all()
    assert rows == []

def test_add_reaction_to_comment_duplicate_is_idempotent(session: Session, test_comment, test_user):
    first = CommentService.add_reaction_to_comment(session, test_comment.mid, test_user.uid, ReactionType.LIKE)
    second = CommentService.add_reaction_to_comment(session, test_comment.mid, test_user.uid, ReactionType.LIKE)

    assert first is not None
    assert second is not None

    reactions = session.exec(
        select(CommentReaction).where(
            CommentReaction.mid == test_comment.mid,
            CommentReaction.uid == test_user.uid,
        )
    ).all()
    assert len(reactions) == 1

    stats = session.get(CommentStats, test_comment.mid)
    assert stats.likes == 1
    assert stats.dislikes == 0
