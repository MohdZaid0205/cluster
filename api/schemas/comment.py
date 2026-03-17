from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from api.models.enums import ReactionType

class CommentCreate(BaseModel):
    """
    Schema handling the underlying creation payload for a new comment or reply.
    """
    uid       : UUID                                                           # ID of the creating user
    content   : str                                                            # Text payload of the comment
    pid       : Optional[UUID] = None                                          # Reference to a post, if root comment
    parent_mid: Optional[UUID] = None                                          # Reference to another comment, if a reply

class CommentResponse(BaseModel):
    """
    Readout schema defining how a comment is structured when returned to the client.
    """
    mid       : UUID                                                           # Unique comment ID
    uid       : UUID                                                           # Reference to authoring user
    pid       : Optional[UUID] = None                                          # Reference to parent post
    parent_mid: Optional[UUID] = None                                          # Reference to parent comment
    content   : str                                                            # Display content
    created_at: datetime                                                       # Timestamp of creation
    likes     : int            = 0                                             # Total likes accrued
    dislikes  : int            = 0                                             # Total dislikes accrued

class CommentReactionCreate(BaseModel):
    """
    Schema for validating interaction payloads specifically targeting comments.
    """
    uid          : UUID                                                        # User acting on the comment
    reaction_type: ReactionType                                                # The chosen reaction type
