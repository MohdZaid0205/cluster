import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from uuid import uuid4

from api.main import app
from api.database import get_session
from api.models.user import UserAuth, UserProfile, UserRole
from api.security import get_password_hash
from api.triggers import apply_triggers_now

# Setup perfectly isolated in-memory SQLite database
DATABASE_URL = "sqlite://"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    apply_triggers_now(engine)       # install the 5 SQLite triggers on the live connection
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_password")
def test_password_fixture():
    return "secure_password_123"

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user):
    from api.auth import create_access_token
    token = create_access_token(data={"sub": str(test_user.uid)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session, test_password):
    """Creates a standard verified user for testing."""
    uid = uuid4()
    user = UserAuth(
        uid=uid,
        email="test@example.com",
        password_hash=get_password_hash(test_password),
        role=UserRole.VERIFIED,
        is_verified=True
    )
    profile = UserProfile(
        uid=uid,
        name="Test User",
        bio="I am a test user.",
        location="Test City"
    )
    
    session.add(user)
    session.add(profile)
    session.commit()
    
    return user

from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember
from api.models.post import PostCore, PostContent, PostStats, PostType
from api.models.comment import CommentCore, CommentContent, CommentStats

@pytest.fixture(name="test_cluster")
def test_cluster_fixture(session: Session, test_user):
    cid = uuid4()
    core = ClusterCore(cid=cid, name="Global Test Cluster", category="Testing", is_private=False)
    info = ClusterInfo(cid=cid, description="A global test cluster", creator_uid=test_user.uid)
    # Start at 0 — trg_increment_member_count will bump to 1 when member row inserted
    stats = ClusterStats(cid=cid, member_count=0)
    member = ClusterMember(cid=cid, uid=test_user.uid, role="MODERATOR")
    
    session.add(core)
    session.add(info)
    session.add(stats)
    session.add(member)
    session.commit()
    session.expire_all()
    
    return core

@pytest.fixture(name="test_post")
def test_post_fixture(session: Session, test_user, test_cluster):
    pid = uuid4()
    core = PostCore(pid=pid, uid=test_user.uid, cid=test_cluster.cid, type=PostType.TEXT)
    content = PostContent(pid=pid, content="Global Test Post")
    #stats = PostStats(pid=pid)
    
    session.add(core)
    session.add(content)
    session.commit()
    session.expire_all()
    
    return core

@pytest.fixture(name="test_comment")
def test_comment_fixture(session: Session, test_user, test_post):
    mid = uuid4()
    core = CommentCore(mid=mid, uid=test_user.uid, pid=test_post.pid)
    content = CommentContent(mid=mid, content="Global Test Comment")
    # stats = CommentStats(mid=mid)
    
    session.add(core)
    session.add(content)
    session.commit()
    session.expire_all()
    
    return core
