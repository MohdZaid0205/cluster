from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from api.models.enums import ClusterRole

class ClusterCreate(BaseModel):
    """
    Schema for validating properties when explicitly creating a new cluster.
    """
    name        : str                                                              # Name of the cluster
    category    : Optional[str]      = None                                        # The main categorization or theme
    is_private  : Optional[bool]     = False                                       # Privacy guard flag
    description : Optional[str]      = None                                        # Full text description
    tags        : Optional[str]      = None                                        # Raw comma-separated string of related tags
    profile_icon: Optional[str]      = None                                        # Initial image URL for the cluster's context art
    creator_uid : UUID                                                             # ID of the user requesting the creation

class ClusterResponse(BaseModel):
    """
    Abstract, brief representation of a cluster used in listing and summarized responses.
    """
    cid         : UUID                                                             # Unique identifier of the cluster
    name        : str                                                              # Cluster display name
    category    : Optional[str]      = None                                        # Cluster categorization
    is_private  : bool                                                             # Indicates active privacy settings
    profile_icon: Optional[str]      = None                                        # Display URL for the icon

class ClusterDetailResponse(ClusterResponse):
    """
    Detailed readout schema for a specific cluster including deep metadata and stats.
    """
    description : Optional[str]      = None                                        # Expanded text description
    creator_uid : UUID                                                             # Referencing ID to the user that owns it
    created_at  : datetime                                                         # Timestamp marking when it was spawned
    tags        : Optional[str]      = None                                        # Extrapolated tags
    member_count: int                = 0                                           # Real-time tally of participants

class ClusterMemberCreate(BaseModel):
    """
    Schema defining the payload required when explicitly assigning a user to a cluster.
    """
    uid         : UUID                                                             # Referencing user's system ID
    role        : Optional[ClusterRole] = ClusterRole.MEMBER                       # Target role within the cluster context
