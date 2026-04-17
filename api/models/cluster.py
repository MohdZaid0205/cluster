from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime, UTC
from sqlmodel import Field, SQLModel
from api.models.enums import ClusterRole, RuleAction

class ClusterCore(SQLModel, table=True):
    """
    Contains the foundational data for a cluster including its identity and privacy.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(default_factory=uuid4, primary_key=True) # Unique identifier for the cluster
    name        : str            = Field(index=True)                              # Display name of the cluster
    category    : Optional[str]  = Field(default=None, index=True)                # Broad category under which the cluster falls
    is_private  : bool           = Field(default=False, index=True)               # Flag indicating if cluster requires invite
    profile_icon: Optional[str]  = None                                           # URL to the cluster's profile icon

class ClusterInfo(SQLModel, table=True):
    """
    Contains extended metadata and descriptive details for a cluster.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Foreign key linked to ClusterCore
    description : Optional[str]  = None                                                   # Detailed description of the cluster
    creator_uid : UUID           = Field(foreign_key="userauth.uid", index=True)          # User ID of the cluster's creator
    created_at  : datetime       = Field(default_factory=lambda: datetime.now(UTC))                 # Timestamp of cluster creation
    tags        : Optional[str]  = None                                                   # Comma-separated tags for search

class ClusterStats(SQLModel, table=True):
    """
    Tracks analytical and statistical data for a cluster over time.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Foreign key linked to ClusterCore
    member_count: int            = 0                                                      # Total number of members in the cluster

class ClusterMember(SQLModel, table=True):
    """
    Represents a user's membership and active role within a specific cluster.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Foreign key linked to ClusterCore
    uid         : UUID           = Field(primary_key=True, foreign_key="userauth.uid")    # User ID of the member
    joined_at   : datetime       = Field(default_factory=lambda: datetime.now(UTC))                 # Timestamp when user joined
    role        : ClusterRole    = Field(default=ClusterRole.MEMBER)                      # Predefined role within the cluster

class ClusterBookmark(SQLModel, table=True):
    """
    Stores per-user bookmarked clusters for quick access in the UI.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Cluster being bookmarked
    uid         : UUID           = Field(primary_key=True, foreign_key="userauth.uid")    # Bookmark owner
    bookmarked_at: datetime      = Field(default_factory=lambda: datetime.now(UTC))         # Timestamp when bookmark was created

class ClusterChatOption(SQLModel, table=True):
    """
    Stores per-user chat preference for each cluster.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Cluster being configured
    uid         : UUID           = Field(primary_key=True, foreign_key="userauth.uid")    # Owner of the preference
    chat_enabled: bool           = Field(default=True)                                       # Whether cluster chat is enabled for this user
    updated_at  : datetime       = Field(default_factory=lambda: datetime.now(UTC))         # Last update timestamp

class ClusterModerator(SQLModel, table=True):
    """
    Tracks users who have been explicitly assigned moderator capabilities.
    """
    __table_args__ = {"extend_existing": True}

    cid         : UUID           = Field(primary_key=True, foreign_key="clustercore.cid") # Foreign key linked to ClusterCore
    uid         : UUID           = Field(primary_key=True, foreign_key="userauth.uid")    # User ID of the moderator
    assigned_at : datetime       = Field(default_factory=lambda: datetime.now(UTC))                 # Timestamp when moderation was assigned

class ClusterRule(SQLModel, table=True):
    """
    Defines an automated moderation or structural rule enforced within a cluster.
    """
    __table_args__ = {"extend_existing": True}

    rid         : UUID           = Field(default_factory=uuid4, primary_key=True)         # Unique identifier for the rule
    cid         : UUID           = Field(index=True, foreign_key="clustercore.cid")       # Foreign key linked to ClusterCore
    name        : str                                                                     # Human-readable name of the rule
    pattern     : str                                                                     # Regex or logical pattern to match against
    action      : RuleAction                                                              # Action taken when rule is matched
    description : Optional[str]  = None                                                   # Expanded explanation of the rule's purpose
