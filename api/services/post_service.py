from sqlmodel import Session, select, func, desc, or_
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from api.models.post import PostCore, PostContent, PostStats, PostReaction, Window, Megaphone
from api.models.cluster import ClusterMember
from api.models.user import UserProfile
from api.models.enums import ReactionType

class PostService:
    """
    Handles read-heavy aggregations, feeds, and analytic extractions from posts.
    """

    @staticmethod
    def get_post_full_details(session: Session, pid: UUID):
        """
        Retrieves all joined core properties of a specific post.
        Maps to: GET FULL POST DETAILS BY ID
        """
        statement = (
            select(PostCore, PostContent, PostStats)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .where(PostCore.pid == pid)
        )
        return session.exec(statement).first()

    @staticmethod
    def get_recent_posts_for_cluster(session: Session, cid: UUID, limit: int = 50):
        """
        Feed generator for a specific cluster container.
        Maps to: LIST ALL POSTS IN A SPECIFIC CLUSTER
        """
        statement = (
            select(PostCore.pid, PostContent.content, PostStats.likes, PostCore.created_at)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .where(PostCore.cid == cid)
            .order_by(desc(PostCore.created_at))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_recent_posts_by_user(session: Session, uid: UUID, limit: int = 50):
        """
        Feed generator for a specific user's public profile.
        Maps to: LIST ALL POSTS BY A SPECIFIC USER
        """
        statement = (
            select(PostCore.pid, PostContent.content, PostStats.likes, PostCore.created_at)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .where(PostCore.uid == uid)
            .order_by(desc(PostCore.created_at))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_liked_posts_in_cluster(session: Session, cid: UUID, limit: int = 5):
        """
        Quality analytics finding the most lauded content in a cluster.
        Maps to: TOP 5 MOST LIKED POSTS IN A CLUSTER
        """
        statement = (
            select(PostContent.content, PostStats.likes)
            .join(PostStats, PostContent.pid == PostStats.pid)
            .join(PostCore, PostContent.pid == PostCore.pid)
            .where(PostCore.cid == cid)
            .order_by(desc(PostStats.likes))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_most_controversial_posts_in_cluster(session: Session, cid: UUID, limit: int = 5):
        """
        Analytics finding heavily downvoted content in a cluster.
        Maps to: TOP 5 MOST CONTROVERSIAL POSTS
        """
        statement = (
            select(PostContent.content, PostStats.dislikes)
            .join(PostStats, PostContent.pid == PostStats.pid)
            .join(PostCore, PostContent.pid == PostCore.pid)
            .where(PostCore.cid == cid)
            .order_by(desc(PostStats.dislikes))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def list_users_who_liked_post(session: Session, pid: UUID):
        """
        Retrieves the profile names of users who engaged positively.
        Maps to: LIST USERS WHO LIKED A SPECIFIC POST
        """
        statement = (
            select(UserProfile.name, PostReaction.timestamp)
            .join(UserProfile, PostReaction.uid == UserProfile.uid)
            .where(PostReaction.pid == pid)
            .where(PostReaction.reaction_type == ReactionType.LIKE)
        )
        return session.exec(statement).all()

    @staticmethod
    def count_post_reactions_by_type(session: Session, pid: UUID):
        """
        Aggregates reaction distributions for charting.
        Maps to: COUNT REACTIONS BY TYPE FOR A POST
        """
        statement = (
            select(PostReaction.reaction_type, func.count(PostReaction.reaction_type).label("count"))
            .where(PostReaction.pid == pid)
            .group_by(PostReaction.reaction_type)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_active_megaphones(session: Session):
        """
        Fetches currently promoted global posts.
        Maps to: LIST ALL ACTIVE MEGAPHONES
        """
        statement = (
            select(PostCore.pid, PostContent.content, Megaphone.type, Megaphone.end_time)
            .join(PostCore, Megaphone.pid == PostCore.pid)
            .join(PostContent, Megaphone.pid == PostContent.pid)
            .where(Megaphone.is_active == True)
            .where(Megaphone.end_time > datetime.now())
        )
        return session.exec(statement).all()

    @staticmethod
    def get_windows_for_post(session: Session, origin_pid: UUID):
        """
        Retrieves instances where a post has been embedded/shared elsewhere.
        Maps to: FIND ALL WINDOWS (SHARES) OF A SPECIFIC ORIGINAL POST
        """
        statement = (
            select(Window.wid, UserProfile.name.label("shared_by"), Window.created_at)
            .join(UserProfile, Window.shared_by_uid == UserProfile.uid)
            .where(Window.origin_pid == origin_pid)
            .order_by(desc(Window.created_at))
        )
        return session.exec(statement).all()

    @staticmethod
    def get_homepage_feed_for_user(session: Session, uid: UUID, limit: int = 50):
        """
        Generates a custom feed by extracting posts only from clusters the user is a member of.
        """
        statement = (
            select(PostCore, PostContent, PostStats)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            .join(ClusterMember, PostCore.cid == ClusterMember.cid)
            .where(ClusterMember.uid == uid)
            .order_by(desc(PostCore.created_at))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_trending_posts_globally(session: Session, limit: int = 20):
        """
        Retrieves universally trending content across all public clusters based on like velocity.
        """
        statement = (
            select(PostCore, PostContent, PostStats)
            .join(PostContent, PostCore.pid == PostContent.pid)
            .join(PostStats, PostCore.pid == PostStats.pid)
            # .join(ClusterCore).where(ClusterCore.is_private == False)
            .order_by(desc(PostStats.likes)) # Simple approximation of trending
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def create_post(session: Session, post_in):
        """
        Initializes a post including its content payload.
        PostStats is auto-created by the trg_init_post_stats trigger.
        """
        try:
            core_post = PostCore(
                uid  = post_in.uid,
                cid  = post_in.cid,
                type = post_in.type
            )
            session.add(core_post)
            session.flush()  # generate pid before FK inserts

            content = PostContent(
                pid     = core_post.pid,
                content = post_in.content,
                tags    = post_in.tags
            )
            session.add(content)
            session.commit()          # trigger fires here, creating PostStats
            session.expire_all()      # clear cache so we see trigger-created rows

            session.refresh(core_post)
            session.refresh(content)
            stats = session.get(PostStats, core_post.pid)

            return core_post, content, stats
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def delete_post(session: Session, pid: UUID):
        """
        Deletes a post completely from the system.
        """
        post = session.get(PostCore, pid)
        if not post: return False
        session.delete(post)
        session.commit()
        return True

    @staticmethod
    def add_reaction_to_post(session: Session, pid: UUID, uid: UUID, reaction_type):
        """
        Registers a reaction and updates the aggregated statistics payload.
        """
        try:
            # Ensure only 1 reaction per user per post exists by clearing previous
            existing_Reaction = session.exec(select(PostReaction).where(PostReaction.pid == pid, PostReaction.uid == uid)).first()
            stats = session.get(PostStats, pid)
            
            if existing_Reaction:
                if existing_Reaction.reaction_type == reaction_type:
                    return existing_Reaction # No change
                # Decrease old stat counter
                if existing_Reaction.reaction_type.name == "LIKE" and stats: stats.likes -= 1
                elif existing_Reaction.reaction_type.name == "DISLIKE" and stats: stats.dislikes -= 1
                session.delete(existing_Reaction)
            
            reaction = PostReaction(pid=pid, uid=uid, reaction_type=reaction_type)
            session.add(reaction)
            
            if reaction_type.name == "LIKE" and stats: stats.likes += 1
            elif reaction_type.name == "DISLIKE" and stats: stats.dislikes += 1
            
            if stats: session.add(stats)
            session.commit()
            return reaction
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def remove_reaction_from_post(session: Session, pid: UUID, uid: UUID):
        """
        Unregisters a user's reaction from a post and decrements stats.
        """
        try:
            existing_Reaction = session.exec(select(PostReaction).where(PostReaction.pid == pid, PostReaction.uid == uid)).first()
            if existing_Reaction:
                stats = session.get(PostStats, pid)
                if existing_Reaction.reaction_type.name == "LIKE" and stats: stats.likes -= 1
                elif existing_Reaction.reaction_type.name == "DISLIKE" and stats: stats.dislikes -= 1
                if stats: session.add(stats)
                session.delete(existing_Reaction)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
