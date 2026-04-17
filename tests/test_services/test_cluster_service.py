import pytest
from uuid import uuid4
from sqlmodel import Session, select
from api.services.cluster_service import ClusterService
from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember
from api.models.user import UserAuth, UserProfile, UserRole

@pytest.fixture(name="test_cluster")
def test_cluster_fixture(session: Session, test_user):
    class MockClusterIn:
        name = "Test Cluster"
        category = "Tech"
        is_private = False
        profile_icon = "icon.jpg"
        description = "A test cluster"
        creator_uid = test_user.uid
        tags = "test, tech"
        
    core, info, stats = ClusterService.create_cluster(session, MockClusterIn())
    return core

def test_create_cluster(session: Session, test_user):
    class MockClusterIn:
        name = "New Test Cluster"
        category = "Science"
        is_private = True
        profile_icon = "icon2.jpg"
        description = "Another test cluster"
        creator_uid = test_user.uid
        tags = "science"
        
    core, info, stats = ClusterService.create_cluster(session, MockClusterIn())
    
    assert core is not None
    assert core.name == "New Test Cluster"
    assert info.description == "Another test cluster"
    assert stats.member_count == 1  # Creator is added
    
    member = ClusterService.check_user_membership(session, core.cid, test_user.uid)
    assert member is not None

def test_get_public_clusters_by_popularity(session: Session, test_cluster):
    clusters = ClusterService.get_public_clusters_by_popularity(session)
    assert len(clusters) > 0
    assert clusters[0][0].cid == test_cluster.cid

def test_search_clusters_by_name(session: Session, test_cluster):
    clusters = ClusterService.search_clusters_by_name(session, "Test")
    assert len(clusters) > 0
    assert clusters[0].cid == test_cluster.cid

def test_add_and_remove_user_from_cluster(session: Session, test_cluster):
    # Create another user
    new_uid = uuid4()
    user = UserAuth(uid=new_uid, email="user2@example.com", password_hash="hash", role=UserRole.MEMBER)
    session.add(user)
    session.commit()
    
    # Add User
    member = ClusterService.add_user_to_cluster(session, test_cluster.cid, new_uid)
    assert member is not None
    assert member.uid == new_uid
    
    # Check stats increased (creator = 1, new user = 2)
    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == 2
    
    # Remove User
    success = ClusterService.remove_user_from_cluster(session, test_cluster.cid, new_uid)
    assert success is True
    
    # Check stats decreased
    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == 1

def test_add_user_to_cluster_duplicate_is_idempotent(session: Session, test_cluster):
    new_uid = uuid4()
    user = UserAuth(uid=new_uid, email="user3@example.com", password_hash="hash", role=UserRole.MEMBER)
    session.add(user)
    session.commit()

    first = ClusterService.add_user_to_cluster(session, test_cluster.cid, new_uid)
    second = ClusterService.add_user_to_cluster(session, test_cluster.cid, new_uid)

    assert first is not None
    assert second is not None

    member_rows = session.exec(
        select(ClusterMember).where(
            ClusterMember.cid == test_cluster.cid,
            ClusterMember.uid == new_uid,
        )
    ).all()
    assert len(member_rows) == 1

    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == 2
