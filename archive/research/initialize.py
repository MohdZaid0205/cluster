import os
from uuid import uuid4, UUID
from datetime import datetime, UTC, timedelta
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, create_engine
import sys

# Ensure this script can find the 'api' package from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from api.triggers import apply_triggers_now

# --- Setup ---
os.makedirs("archive/research", exist_ok=True)
os.makedirs("temp/db", exist_ok=True)
DATABASE_URL = "sqlite:///temp/db/research.db"
engine = create_engine(DATABASE_URL, echo=False)

# --- Enums ---
class UserRole(str, Enum):
    GUEST = "GUEST"
    MEMBER = "MEMBER"
    VERIFIED = "VERIFIED"
    ADMIN = "ADMIN"

class ClusterRole(str, Enum):
    MEMBER = "MEMBER"
    MODERATOR = "MODERATOR"

class PostType(str, Enum):
    TEXT = "TEXT"
    LINK = "LINK"
    WINDOW = "WINDOW"

class ReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    LOVE = "LOVE"
    LAUGH = "LAUGH"
    SAD = "SAD"
    WOW = "WOW"
    ANGRY = "ANGRY"

class MegaphoneType(str, Enum):
    ANNOUNCEMENT = "ANNOUNCEMENT"
    POLL = "POLL"
    EVENT = "EVENT"

class EventRsvpStatus(str, Enum):
    GOING = "GOING"
    MAYBE = "MAYBE"
    NOT_GOING = "NOT_GOING"

class RuleAction(str, Enum):
    BLOCK = "BLOCK"
    FLAG = "FLAG"

# --- Schema Definitions (Fragmented) ---

# 1. User
class UserAuth(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    email: Optional[str] = Field(default=None, index=True, sa_column_kwargs={"unique": True})
    phone: Optional[str] = Field(default=None, index=True, sa_column_kwargs={"unique": True})
    password_hash: str
    role: UserRole = Field(default=UserRole.MEMBER)
    is_verified: bool = Field(default=False)

class UserProfile(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    profile_image: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active: datetime = Field(default_factory=lambda: datetime.now(UTC))

# 2. Cluster
class ClusterCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    category: Optional[str] = Field(default=None, index=True)
    is_private: bool = Field(default=False)
    profile_icon: Optional[str] = None

class ClusterInfo(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    description: Optional[str] = None
    creator_uid: UUID = Field(foreign_key="userauth.uid")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tags: Optional[str] = None

class ClusterStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    member_count: int = 0

# Cluster Relations
class ClusterMember(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    role: ClusterRole = Field(default=ClusterRole.MEMBER)

class ClusterModerator(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class ClusterRule(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    rid: UUID = Field(default_factory=uuid4, primary_key=True)
    cid: UUID = Field(index=True, foreign_key="clustercore.cid")
    name: str
    pattern: str
    action: RuleAction
    description: Optional[str] = None

# 3. Post
class PostCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(default_factory=uuid4, primary_key=True)
    uid: UUID = Field(index=True, foreign_key="userauth.uid")
    cid: UUID = Field(index=True, foreign_key="clustercore.cid")
    type: PostType = Field(default=PostType.TEXT)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    updated_at: Optional[datetime] = None

class PostContent(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    content: str
    tags: Optional[str] = None

class PostStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    likes: int = 0
    dislikes: int = 0

# Post Relations
class PostReaction(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    reaction_type: ReactionType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Window(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    wid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    origin_pid: UUID = Field(foreign_key="postcore.pid")
    shared_by_uid: UUID = Field(foreign_key="userauth.uid")
    shared_into_cid: UUID = Field(foreign_key="clustercore.cid")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Megaphone(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    start_time: datetime
    end_time: datetime
    type: MegaphoneType
    is_active: bool = True
    subscriber_count: int = 0

class UserFollow(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    follower_uid: UUID = Field(foreign_key="userauth.uid", primary_key=True)
    following_uid: UUID = Field(foreign_key="userauth.uid", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class MegaphonePollOption(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(foreign_key="postcore.pid", primary_key=True)
    idx: int = Field(primary_key=True)
    label: str

class MegaphonePollVote(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(foreign_key="postcore.pid", primary_key=True)
    uid: UUID = Field(foreign_key="userauth.uid", primary_key=True)
    option_idx: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class MegaphoneEventMeta(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    location: Optional[str] = None

class MegaphoneEventRsvp(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(foreign_key="postcore.pid", primary_key=True)
    uid: UUID = Field(foreign_key="userauth.uid", primary_key=True)
    status: EventRsvpStatus
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# 4. Comment
class CommentCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(default_factory=uuid4, primary_key=True)
    uid: UUID = Field(foreign_key="userauth.uid")
    pid: Optional[UUID] = Field(default=None,  index=True, foreign_key="postcore.pid")
    parent_mid: Optional[UUID] = Field(default=None, index=True, foreign_key="commentcore.mid")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

class CommentContent(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    content: str

class CommentStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    likes: int = 0
    dislikes: int = 0

class CommentReaction(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    reaction_type: ReactionType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

def main():
    print("Initializing Database Structure...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    print("Applying Database Triggers...")
    apply_triggers_now(engine)
    
    print("Tables and triggers created successfully, no data generated.")

if __name__ == "__main__":
    main()
