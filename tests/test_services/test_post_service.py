import pytest
from uuid import uuid4
from sqlmodel import Session
from api.services.post_service import PostService
from api.services.cluster_service import ClusterService
from api.models.post import PostCore, PostContent, PostStats, PostType, PostReaction
from api.models.enums import ReactionType

@pytest.fixture(name="test_post")
def test_post_fixture(session: Session, test_user, test_cluster):
    class MockPostIn:
        uid = test_user.uid
        cid = test_cluster.cid
        type = PostType.TEXT
        content = "This is a test post"
        tags = "test"
        
    core, content, stats = PostService.create_post(session, MockPostIn())
    return core

def test_create_post(session: Session, test_user, test_cluster):
    class MockPostIn:
        uid = test_user.uid
        cid = test_cluster.cid
        type = PostType.LINK
        content = "https://example.com"
        tags = "link"
        
    core, content, stats = PostService.create_post(session, MockPostIn())
    
    assert core is not None
    assert core.type == PostType.LINK
    assert content.content == "https://example.com"
    assert stats.likes == 0
    assert stats.dislikes == 0

def test_get_post_full_details(session: Session, test_post):
    result = PostService.get_post_full_details(session, test_post.pid)
    assert result is not None
    core, content, stats = result
    assert core.pid == test_post.pid
    assert content.content == "This is a test post"

def test_get_recent_posts_for_cluster(session: Session, test_post, test_cluster):
    posts = PostService.get_recent_posts_for_cluster(session, test_cluster.cid)
    assert len(posts) > 0
    assert posts[0].pid == test_post.pid

def test_add_and_remove_reaction(session: Session, test_post, test_user):
    # Add LIKE
    reaction = PostService.add_reaction_to_post(session, test_post.pid, test_user.uid, ReactionType.LIKE)
    assert reaction is not None
    assert reaction.reaction_type == ReactionType.LIKE
    
    # Check stats
    stats = session.get(PostStats, test_post.pid)
    assert stats.likes == 1
    
    # Change to DISLIKE
    reaction = PostService.add_reaction_to_post(session, test_post.pid, test_user.uid, ReactionType.DISLIKE)
    assert reaction.reaction_type == ReactionType.DISLIKE
    stats = session.get(PostStats, test_post.pid)
    assert stats.likes == 0
    assert stats.dislikes == 1
    
    # Remove
    success = PostService.remove_reaction_from_post(session, test_post.pid, test_user.uid)
    assert success is True
    stats = session.get(PostStats, test_post.pid)
    assert stats.dislikes == 0
