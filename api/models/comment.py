from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime
from sqlmodel import Field, SQLModel
from api.models.enums import ReactionType

class CommentCore(SQLModel, table=True):
    """
    Core attributes and relationships defining the existence of a comment.
    """
    __table_args__ = {"extend_existing": True}

    mid       : UUID             = Field(default_factory=uuid4, primary_key=True)         # Unique identifier for the comment
    uid       : UUID             = Field(foreign_key="userauth.uid", index=True)          # ID of the user who authored the comment
    pid       : Optional[UUID]   = Field(default=None, index=True, foreign_key="postcore.pid") # Associated post ID, if applicable
    parent_mid: Optional[UUID]   = Field(default=None, index=True, foreign_key="commentcore.mid") # Parent comment ID, for threads
    created_at: datetime         = Field(default_factory=lambda: datetime.now(), index=True)     # Timestamp when comment was created

class CommentContent(SQLModel, table=True):
    """
    Stores the textual content body of a comment.
    """
    __table_args__ = {"extend_existing": True}

    mid       : UUID             = Field(primary_key=True, foreign_key="commentcore.mid") # Foreign key linked to CommentCore
    content   : str                                                                       # The main body text of the comment

class CommentStats(SQLModel, table=True):
    """
    Aggregated interaction metrics such as likes and dislikes for a comment.
    """
    __table_args__ = {"extend_existing": True}

    mid       : UUID             = Field(primary_key=True, foreign_key="commentcore.mid") # Foreign key linked to CommentCore
    likes     : int              = 0                                                      # Total number of likes
    dislikes  : int              = 0                                                      # Total number of dislikes

class CommentReaction(SQLModel, table=True):
    """
    Represents an individual user's reaction to a specific comment.
    """
    __table_args__ = {"extend_existing": True}

    mid          : UUID          = Field(primary_key=True, foreign_key="commentcore.mid") # Foreign key linked to CommentCore
    uid          : UUID          = Field(primary_key=True, foreign_key="userauth.uid")    # ID of the user reacting
    reaction_type: ReactionType  = Field(index=True)                                      # The specific type of reaction recorded
    timestamp    : datetime      = Field(default_factory=lambda: datetime.now())                 # Timestamp of the reaction
