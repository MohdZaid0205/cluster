# =====================================================================
# API Models Module
# =====================================================================
# Defines all abstract and concrete SQLModel representations pointing
# to the underlying database tables. Importing them all in this central
# initialization file ensures they are registered automatically when Alembic
# or SQLAlchemy spins up, while providing convenient short import paths.
# =====================================================================

from .enums import UserRole, ClusterRole, PostType, ReactionType, MegaphoneType, RuleAction
from .user import UserAuth, UserProfile
from .cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember, ClusterBookmark, ClusterChatOption, ClusterModerator, ClusterRule
from .post import PostCore, PostContent, PostStats, PostReaction, Window, Megaphone
from .comment import CommentCore, CommentContent, CommentStats, CommentReaction

__all__ = [
    # Cluster
    "ClusterCore",
    "ClusterInfo",
    "ClusterStats",
    "ClusterMember",
    "ClusterBookmark",
    "ClusterChatOption",
    "ClusterModerator",
    "ClusterRule",
    "ClusterRole",

    # User
    "UserAuth",
    "UserProfile",
    "UserRole",

    # Post
    "PostCore",
    "PostContent",
    "PostStats",
    "PostReaction",
    "Window",
    "Megaphone",
    "PostType",
    "ReactionType",
    "MegaphoneType",

    # Comment
    "CommentCore",
    "CommentContent",
    "CommentStats",
    "CommentReaction",

    # Rules / Other
    "RuleAction"
]
