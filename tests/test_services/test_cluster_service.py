import pytest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlmodel import Session
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


def test_simultaneous_join_same_user_is_idempotent(session: Session, test_cluster):
    """
    Two concurrent join attempts for the same user should not crash and should
    create only one membership row.
    """
    new_uid = uuid4()
    user = UserAuth(uid=new_uid, email="same-user-race@example.com", password_hash="hash", role=UserRole.MEMBER)
    session.add(user)
    session.commit()

    engine = session.get_bind()

    def join_once():
        with Session(engine) as local_session:
            _member, created = ClusterService.add_user_to_cluster(
                local_session,
                test_cluster.cid,
                new_uid,
                return_created=True,
            )
            return created

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: join_once(), range(2)))

    assert sum(results) == 1
    assert ClusterService.check_user_membership(session, test_cluster.cid, new_uid) is not None
    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == 2  # creator + exactly one joined user


def test_simultaneous_join_two_users_both_succeed(session: Session, test_cluster):
    """
    Two concurrent joins for different users should both be applied.
    """
    uid_a = uuid4()
    uid_b = uuid4()
    session.add(UserAuth(uid=uid_a, email="race-a@example.com", password_hash="hash", role=UserRole.MEMBER))
    session.add(UserAuth(uid=uid_b, email="race-b@example.com", password_hash="hash", role=UserRole.MEMBER))
    session.commit()

    engine = session.get_bind()

    def join_once(target_uid):
        with Session(engine) as local_session:
            _member, created = ClusterService.add_user_to_cluster(
                local_session,
                test_cluster.cid,
                target_uid,
                return_created=True,
            )
            return created

    with ThreadPoolExecutor(max_workers=2) as executor:
        created_a, created_b = list(executor.map(join_once, [uid_a, uid_b]))

    assert created_a is True
    assert created_b is True
    assert ClusterService.check_user_membership(session, test_cluster.cid, uid_a) is not None
    assert ClusterService.check_user_membership(session, test_cluster.cid, uid_b) is not None
    stats = session.get(ClusterStats, test_cluster.cid)
    assert stats.member_count == 3  # creator + two joined users
