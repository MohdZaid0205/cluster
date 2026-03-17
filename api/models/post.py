from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime, UTC
from sqlmodel import Field, SQLModel
from api.models.enums import PostType, ReactionType, MegaphoneType

class PostCore(SQLModel, table=True):
    """
    Core attributes and relationships defining the existence of a post.
    """
    __table_args__ = {"extend_existing": True}

    pid       : UUID             = Field(default_factory=uuid4, primary_key=True)         # Unique identifier for the post
    uid       : UUID             = Field(index=True, foreign_key="userauth.uid")          # ID of the user who authored the post
    cid       : UUID             = Field(index=True, foreign_key="clustercore.cid")       # ID of the cluster where the post lives
    type      : PostType         = Field(default=PostType.TEXT)                           # The type or format of the post
    created_at: datetime         = Field(default_factory=lambda: datetime.now(UTC), index=True)     # Timestamp when the post was created
    updated_at: Optional[datetime] = None                                                 # Timestamp of the last edit

class PostContent(SQLModel, table=True):
    """
    Stores the actual text content and categorized tags of a post.
    """
    __table_args__ = {"extend_existing": True}

    pid       : UUID             = Field(primary_key=True, foreign_key="postcore.pid")    # Foreign key linked to PostCore
    content   : str                                                                       # Main body content of the post
    tags      : Optional[str]    = None                                                   # Comma-separated tags for the post

class PostStats(SQLModel, table=True):
    """
    Aggregated interaction metrics such as likes and dislikes for a post.
    """
    __table_args__ = {"extend_existing": True}

    pid       : UUID             = Field(primary_key=True, foreign_key="postcore.pid")    # Foreign key linked to PostCore
    likes     : int              = 0                                                      # Total number of likes
    dislikes  : int              = 0                                                      # Total number of dislikes

class PostReaction(SQLModel, table=True):
    """
    Represents an individual user's reaction to a specific post.
    """
    __table_args__ = {"extend_existing": True}

    pid          : UUID          = Field(primary_key=True, foreign_key="postcore.pid")    # Foreign key linked to PostCore
    uid          : UUID          = Field(primary_key=True, foreign_key="userauth.uid")    # ID of the user reacting
    reaction_type: ReactionType  = Field(index=True)                                      # The specific type of reaction recorded
    timestamp    : datetime      = Field(default_factory=lambda: datetime.now(UTC))                 # Timestamp of the reaction

class Window(SQLModel, table=True):
    """
    A special type of post that re-shares an existing post into a different context.
    """
    __table_args__ = {"extend_existing": True}

    wid            : UUID        = Field(primary_key=True, foreign_key="postcore.pid")    # Foreign key linked to PostCore
    origin_pid     : UUID        = Field(foreign_key="postcore.pid")                      # ID of the original post being shared
    shared_by_uid  : UUID        = Field(foreign_key="userauth.uid")                      # User who shared the post
    shared_into_cid: UUID        = Field(foreign_key="clustercore.cid")                   # Cluster where the post was shared
    created_at     : datetime    = Field(default_factory=lambda: datetime.now(UTC))                 # Timestamp of the sharing action

class Megaphone(SQLModel, table=True):
    """
    A promoted post structure intended to reach a broader audience or serve as an announcement.
    """
    __table_args__ = {"extend_existing": True}

    pid             : UUID       = Field(primary_key=True, foreign_key="postcore.pid")    # Foreign key linked to PostCore
    start_time      : datetime                                                            # When the megaphone promotion begins
    end_time        : datetime                                                            # When the megaphone promotion ends
    type            : MegaphoneType                                                       # Category or style of the megaphone
    is_active       : bool       = True                                                   # Indicates if promotion is currently active
    subscriber_count: int        = 0                                                      # Number of users subscribed for updates
