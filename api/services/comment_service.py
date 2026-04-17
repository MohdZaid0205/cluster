from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, update
from typing import List, Optional
from uuid import UUID

from api.models.comment import CommentCore, CommentContent, CommentStats, CommentReaction
from api.models.post import PostCore
from api.models.user import UserProfile
from api.models.enums import ReactionType

class CommentService:
    """
    Handles retrieving, threading, and statistically ranking comments.
    """

    @staticmethod
    def get_root_comments_for_post(session: Session, pid: UUID):
        """
        Retrieves top-level (direct) comments responding to a specific post.
        Maps to: GET ALL ROOT COMMENTS FOR A POST
        """
        statement = (
            select(CommentCore.mid, CommentContent.content, CommentStats.likes, CommentCore.created_at)
            .join(CommentContent, CommentCore.mid == CommentContent.mid)
            .join(CommentStats, CommentCore.mid == CommentStats.mid)
            .where(CommentCore.pid == pid)
            .where(CommentCore.parent_mid == None)
            .order_by(CommentCore.created_at)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_replies_for_comment(session: Session, parent_mid: UUID):
        """
        Retrieves all nested replies targeting a specific parent comment.
        Maps to: GET REPLIES TO A SPECIFIC COMMENT
        """
        statement = (
            select(CommentCore.mid, CommentContent.content, CommentStats.likes, CommentCore.created_at)
            .join(CommentContent, CommentCore.mid == CommentContent.mid)
            .join(CommentStats, CommentCore.mid == CommentStats.mid)
            .where(CommentCore.parent_mid == parent_mid)
            .order_by(CommentCore.created_at)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_comments_for_post(session: Session, pid: UUID, limit: int = 10):
        """
        Algorithmically surfaces the most constructive (highest likes - dislikes ratio) comments.
        Maps to: GET TOP RANKED COMMENTS FOR A POST
        """
        statement = (
            select(
                CommentContent.content,
                CommentStats.likes,
                CommentStats.dislikes,
                (CommentStats.likes - CommentStats.dislikes).label("score")
            )
            .join(CommentContent, CommentCore.mid == CommentContent.mid)
            .join(CommentStats, CommentCore.mid == CommentStats.mid)
            .where(CommentCore.pid == pid)
            .order_by((CommentStats.likes - CommentStats.dislikes).desc())
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def list_users_who_liked_comment(session: Session, mid: UUID):
        """
        Retrieves the profiles of users who left positive engagement on a comment.
        Maps to: LIST USERS WHO LIKED A COMMENT
        """
        statement = (
            select(UserProfile.name, CommentReaction.timestamp)
            .join(UserProfile, CommentReaction.uid == UserProfile.uid)
            .where(CommentReaction.mid == mid)
            .where(CommentReaction.reaction_type == ReactionType.LIKE)
        )
        return session.exec(statement).all()

    @staticmethod
    def check_user_reaction_to_comment(session: Session, mid: UUID, uid: UUID):
        """
        Checks if a user reacted to a comment and retrieves the state.
        Maps to: CHECK IF USER REACTED TO A COMMENT
        """
        statement = (
            select(CommentReaction.reaction_type)
            .where(CommentReaction.mid == mid)
            .where(CommentReaction.uid == uid)
        )
        return session.exec(statement).first()

    @staticmethod
    def create_comment(session: Session, comment_in):
        """
        Spawns a new comment entity and its content text.
        CommentStats is auto-created by the trg_init_comment_stats trigger.
        """
        try:
            pid = comment_in.pid
            parent_mid = comment_in.parent_mid

            if not pid and not parent_mid:
                raise ValueError("Comment must belong to a post or another comment")

            if parent_mid:
                parent_comment = session.get(CommentCore, parent_mid)
                if not parent_comment:
                    raise ValueError("Parent comment not found")
                if pid and parent_comment.pid != pid:
                    raise ValueError("Reply post id does not match parent comment")
                pid = parent_comment.pid

            if not pid or not session.get(PostCore, pid):
                raise ValueError("Post not found")

            core_comment = CommentCore(
                uid        = comment_in.uid,
                pid        = pid,
                parent_mid = parent_mid
            )
            session.add(core_comment)
            session.flush()  # generate mid before FK inserts

            content = CommentContent(
                mid     = core_comment.mid,
                content = comment_in.content
            )
            session.add(content)
            session.commit()          # trigger fires here, creating CommentStats
            stats = session.get(CommentStats, core_comment.mid)

            return core_comment, content, stats
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def delete_comment(session: Session, mid: UUID):
        """
        Wipes a comment entity and cascade sweeps its descendants.
        """
        comment = session.get(CommentCore, mid)
        if not comment: return False
        session.delete(comment)
        session.commit()
        return True

    @staticmethod
    def add_reaction_to_comment(session: Session, mid: UUID, uid: UUID, reaction_type):
        """
        Appends or updates a user rating action on a specific comment.
        """
        try:
            existing_Reaction = session.exec(select(CommentReaction).where(CommentReaction.mid == mid, CommentReaction.uid == uid)).first()
            stats = session.get(CommentStats, mid)
            
            if existing_Reaction:
                if existing_Reaction.reaction_type == reaction_type:
                    return existing_Reaction
                if existing_Reaction.reaction_type.name == "LIKE" and stats:
                    session.exec(update(CommentStats).where(CommentStats.mid == mid).values(likes=CommentStats.likes - 1))
                elif existing_Reaction.reaction_type.name == "DISLIKE" and stats:
                    session.exec(update(CommentStats).where(CommentStats.mid == mid).values(dislikes=CommentStats.dislikes - 1))
                session.delete(existing_Reaction)
            
            reaction = CommentReaction(mid=mid, uid=uid, reaction_type=reaction_type)
            session.add(reaction)
            
            if reaction_type.name == "LIKE" and stats:
                session.exec(update(CommentStats).where(CommentStats.mid == mid).values(likes=CommentStats.likes + 1))
            elif reaction_type.name == "DISLIKE" and stats:
                session.exec(update(CommentStats).where(CommentStats.mid == mid).values(dislikes=CommentStats.dislikes + 1))
            
            session.commit()
            return reaction
        except IntegrityError:
            session.rollback()
            return session.exec(select(CommentReaction).where(CommentReaction.mid == mid, CommentReaction.uid == uid)).first()
        except Exception as e:
            session.rollback()
            raise e
