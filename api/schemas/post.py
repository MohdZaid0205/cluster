from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from api.models.enums import PostType, ReactionType, MegaphoneType

class PostCreate(BaseModel):
    """
    Schema dictating the incoming payload to publish a new post.
    """
    uid    : UUID                                                                  # ID of the posting user
    cid    : UUID                                                                  # Target cluster ID for the post
    type   : Optional[PostType] = PostType.TEXT                                    # Specific structure category of the post
    content: str                                                                   # Content payload to display
    tags   : Optional[str]      = None                                             # String containing distinct post tags

class MegaphoneResponse(BaseModel):
    start_time      : datetime
    end_time        : datetime
    type            : str
    is_active       : bool
    subscriber_count: int

class WindowOriginResponse(BaseModel):
    origin_pid  : UUID
    origin_cid  : UUID
    cluster_name: Optional[str] = None
    author_name : Optional[str] = None
    author_uid  : UUID
    content     : Optional[str] = None
    created_at  : Optional[datetime] = None

class PostResponse(BaseModel):
    """
    Schema detailing the outbound representation of an existing post.
    """
    pid           : UUID                                                               # Unique ID sequence of the post
    uid           : UUID                                                               # Reference to the authoring user
    cid           : UUID                                                               # Reference to the container cluster
    type          : PostType                                                           # Structure type
    content       : Optional[str]   = None                                             # Payload body if available
    tags          : Optional[str]   = None                                             # Attached tags
    created_at    : datetime                                                           # Timestamp when it was persisted
    likes         : int             = 0                                                # Active total likes
    dislikes      : int             = 0                                                # Active total dislikes
    megaphone     : Optional[MegaphoneResponse] = None                                # Associated megaphone promotion
    window_origin : Optional[WindowOriginResponse] = None                             # For WINDOW posts, the source post info

class PostReactionCreate(BaseModel):
    """
    Schema handling the payload of an incoming user interaction to a post.
    """
    uid          : UUID                                                            # Responding user
    reaction_type: ReactionType                                                    # Specific reaction type signaled
