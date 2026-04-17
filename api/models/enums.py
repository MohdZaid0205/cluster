from enum import Enum

class UserRole(str, Enum):
    """
    Enumerates the standard system roles a user can be assigned.
    """
    GUEST    = "GUEST"
    MEMBER   = "MEMBER"
    VERIFIED = "VERIFIED"
    ADMIN    = "ADMIN"

class ClusterRole(str, Enum):
    """
    Enumerates the roles a member can have within a specific cluster.
    """
    MEMBER   = "MEMBER"
    MODERATOR= "MODERATOR"

class PostType(str, Enum):
    """
    Enumerates the various content structures a post can adopt.
    """
    TEXT     = "TEXT"
    LINK     = "LINK"
    WINDOW   = "WINDOW"

class ReactionType(str, Enum):
    """
    Enumerates the default emotional responses available for user reactions.
    """
    LIKE     = "LIKE"
    DISLIKE  = "DISLIKE"
    LOVE     = "LOVE"
    LAUGH    = "LAUGH"
    SAD      = "SAD"
    WOW      = "WOW"
    ANGRY    = "ANGRY"

class MegaphoneType(str, Enum):
    """
    Enumerates the styles available for a promoted megaphone post.
    """
    ANNOUNCEMENT = "ANNOUNCEMENT"
    POLL         = "POLL"
    EVENT        = "EVENT"

class EventRsvpStatus(str, Enum):
    """RSVP choices for megaphone EVENT type."""
    GOING     = "GOING"
    MAYBE     = "MAYBE"
    NOT_GOING = "NOT_GOING"

class RuleAction(str, Enum):
    """
    Enumerates the automated actions that can be triggered by a cluster rule match.
    """
    BLOCK    = "BLOCK"
    FLAG     = "FLAG"
