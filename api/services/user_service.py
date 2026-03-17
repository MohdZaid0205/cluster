from sqlmodel import Session, select, func, desc, update
from typing import List, Optional
from uuid import UUID

from api.models.user import UserAuth, UserProfile
from api.models.post import PostCore, PostContent, PostStats, PostReaction
from api.models.comment import CommentCore, CommentContent, CommentStats
from api.models.cluster import ClusterCore
from api.security import get_password_hash, verify_password

class UserService:
    """
    Manages user authentication queries and high-level behavioral analytics.
    """

    @staticmethod
    def verify_login_credentials(session: Session, email: str, password_plain: str):
        """
        Validates the user's identity based on email and password hash.
        Maps to: USER CAN LOGIN TO THEIR OWN ACCOUNT
        """
        statement = select(UserAuth).where(UserAuth.email == email)
        user = session.exec(statement).first()
        
        if not user or not verify_password(password_plain, user.password_hash):
            return None
        return user

    @staticmethod
    def get_user_profile_stats(session: Session, email: str, password_plain: str):
        """
        Retrieves the public profile for an authenticated payload.
        Maps to: USER CAN FETCH HIS PROFILE STATS
        """
        # Authenticate first
        user = UserService.verify_login_credentials(session, email, password_plain)
        if not user:
            return None
            
        statement = select(UserProfile).where(UserProfile.uid == user.uid)
        return session.exec(statement).first()

    @staticmethod
    def get_user_posts_across_clusters(session: Session, uid: UUID):
        """
        Lists all content authored by a specific user system-wide.
        Maps to: LIST POSTS CREATED BY A PARTICULAR USER ALL ACROSS THE CLUSTERS
        """
        statement = (
            select(PostCore.uid, PostContent.content, PostContent.tags, PostCore.created_at, PostCore.cid)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .where(PostCore.uid == uid)
            .order_by(desc(PostCore.created_at))
        )
        return session.exec(statement).all()

    @staticmethod
    def get_user_post_distribution(session: Session, uid: UUID):
        """
        Analyzes a user's posting behavior across multiple clusters.
        Maps to: LIST NUMBER OF POSTS CREATED BY A PARTICULAR USER IN A PARTICULAR CLUSTER
        """
        statement = (
            select(PostCore.uid, ClusterCore.name, func.count(PostCore.pid).label("post_count"))
            .join(ClusterCore, PostCore.cid == ClusterCore.cid)
            .where(PostCore.uid == uid)
            .group_by(PostCore.uid, ClusterCore.cid, ClusterCore.name)
            .order_by(desc("post_count"))
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_comments_by_user(session: Session, uid: UUID, limit: int = 5):
        """
        Retrieves the most liked comments ever made by a user.
        Maps to: LIST TOP 5 COMMENTS OF A USER BASED ON LIKES COUNT
        """
        statement = (
            select(CommentCore.uid, CommentContent.content, CommentStats.likes)
            .join(CommentContent, CommentCore.mid == CommentContent.mid)
            .join(CommentStats, CommentCore.mid == CommentStats.mid)
            .where(CommentCore.uid == uid)
            .order_by(desc(CommentStats.likes))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_posts_by_user(session: Session, uid: UUID, limit: int = 5):
        """
        Retrieves the most positively received posts authored by a user.
        Maps to: LIST TOP 5 POSTS OF A USER BASED ON LIKES COUNT
        """
        statement = (
            select(PostCore.uid, PostContent.content, PostStats.likes)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .where(PostCore.uid == uid)
            .order_by(desc(PostStats.likes))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_most_disliked_posts_by_user(session: Session, uid: UUID, limit: int = 5):
        """
        Retrieves the most negatively received posts authored by a user.
        Maps to: LIST TOP 5 POSTS OF A USER BASED ON DISLIKES COUNT
        """
        statement = (
            select(PostCore.uid, PostContent.content, PostStats.dislikes)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .where(PostCore.uid == uid)
            .order_by(desc(PostStats.dislikes))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_most_active_verified_users(session: Session, limit: int = 5):
        """
        Ranks top verified users based purely on contribution volume (post count).
        Maps to: LIST TOP 5 USERS BASED ON POST COUNT
        """
        statement = (
            select(PostCore.uid, func.count(PostCore.pid).label("post_count"))
            .join(UserAuth, PostCore.uid == UserAuth.uid)
            .where(UserAuth.is_verified == True)
            .group_by(PostCore.uid)
            .order_by(desc("post_count"))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_most_liked_users(session: Session, limit: int = 5):
        """
        Ranks top overall users based on total aggregate likes accumulated across all posts.
        Maps to: LIST TOP 5 USERS BASED ON AGGREGATE REACTIONS COUNT
        """
        statement = (
            select(PostCore.uid, func.sum(PostStats.likes).label("total_likes"), func.count(PostCore.pid).label("post_count"))
            .join(PostStats, PostCore.pid == PostStats.pid)
            .group_by(PostCore.uid)
            .order_by(desc("total_likes"))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_most_engaged_users(session: Session, limit: int = 5):
        """
        Ranks top users based on how frequently they leave reactions on others' posts.
        Maps to: LIST TOP 5 USERS BASED ON THEIR ENGAGEMENT BASED ON TOTAL REACTION COUNT
        """
        statement = (
            select(PostReaction.uid, func.count(PostReaction.uid).label("reaction_count"))
            .group_by(PostReaction.uid)
            .order_by(desc("reaction_count"))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def verify_user_account(session: Session, uid: UUID, new_email: str):
        """
        Simulates the verification of an account via updating email and boolean flag.
        Maps to: USER VERIFIES HIMSELF AND NOW WE ADD HIS VERIFICATION INFORMATION
        """
        statement = (
            update(UserAuth)
            .where(UserAuth.uid == uid)
            .values(email=new_email, is_verified=True)
        )
        session.exec(statement)
        session.commit()
        return True

    @staticmethod
    def register_user(session: Session, user_in):
        """
        Registers a new identity and constructs their public profile skeleton.
        """
        # Hash the incoming plain text password before persistence
        hashed_password = get_password_hash(user_in.password)
        
        auth_user = UserAuth(
            email         = user_in.email,
            phone         = user_in.phone,
            password_hash = hashed_password,
            role          = user_in.role
        )
        session.add(auth_user)
        session.flush()

        profile = UserProfile(
            uid      = auth_user.uid,
            name     = user_in.name,
            bio      = user_in.bio,
            location = user_in.location
        )
        session.add(profile)
        session.commit()
        session.refresh(auth_user)
        session.refresh(profile)

        return auth_user, profile

    @staticmethod
    def update_user_profile(session: Session, uid: UUID, update_data: dict):
        """
        Applies a dictionary of partial updates to a user's public profile.
        """
        profile = session.get(UserProfile, uid)
        if not profile: return None
        
        for key, value in update_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
                
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile

    @staticmethod
    def delete_user_account(session: Session, uid: UUID):
        """
        Completely purges a user's authentication and profile data. 
        """
        auth = session.get(UserAuth, uid)
        if not auth: return False
        session.delete(auth)
        session.commit()
        return True
