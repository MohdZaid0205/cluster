import time

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, select, func, desc
from typing import List, Optional
from uuid import UUID

from api.models.cluster import ClusterCore, ClusterInfo, ClusterStats, ClusterMember, ClusterModerator, ClusterRule
from api.models.user import UserProfile
from api.models.post import PostCore

class ClusterService:
    """
    Extensive data access service handling complex aggregations, searches,
    and membership analyses for clusters.
    """

    @staticmethod
    def get_public_clusters_by_popularity(session: Session, limit: int = 10):
        """
        Lists public clusters sorted by their member count.
        Maps to: LIST ALL PUBLIC CLUSTERS WITH MEMBER COUNTS
        """
        statement = (
            select(ClusterCore, ClusterStats.member_count)
            .join(ClusterStats, ClusterCore.cid == ClusterStats.cid)
            .where(ClusterCore.is_private == False)
            .order_by(desc(ClusterStats.member_count))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def search_clusters_by_name(session: Session, query_term: str):
        """
        Retrieves clusters matching a specific name pattern.
        Maps to: SEARCH CLUSTERS BY NAME
        """
        statement = select(ClusterCore).where(ClusterCore.name.ilike(f"%{query_term}%"))
        return session.exec(statement).all()

    @staticmethod
    def get_clusters_by_category(session: Session, category: str, limit: int = 10):
        """
        Fetches clusters within a target category, sorted by member count.
        Maps to: LIST CLUSTERS BY CATEGORY
        """
        statement = (
            select(ClusterCore, ClusterStats.member_count)
            .join(ClusterStats, ClusterCore.cid == ClusterStats.cid)
            .where(ClusterCore.category == category)
            .order_by(desc(ClusterStats.member_count))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_cluster_full_profile(session: Session, cid: UUID):
        """
        Aggregates the core, info, and stats structures for an entire cluster profile.
        Maps to: GET FULL CLUSTER PROFILE
        """
        statement = (
            select(ClusterCore, ClusterInfo, ClusterStats)
            .join(ClusterInfo, ClusterCore.cid == ClusterInfo.cid)
            .join(ClusterStats, ClusterCore.cid == ClusterStats.cid)
            .where(ClusterCore.cid == cid)
        )
        return session.exec(statement).first()

    @staticmethod
    def list_cluster_rules(session: Session, cid: UUID):
        """
        Retrieves moderation pattern rules configured for a cluster.
        Maps to: LIST RULES FOR A SPECIFIC CLUSTER
        """
        statement = select(ClusterRule).where(ClusterRule.cid == cid)
        return session.exec(statement).all()

    @staticmethod
    def get_cluster_creator_profile(session: Session, cid: UUID):
        """
        Retrieves public information about the user who created this cluster.
        Maps to: GET CLUSTER CREATOR PROFILE
        """
        statement = (
            select(UserProfile.name, UserProfile.bio, ClusterCore.name.label("cluster_name"))
            .join(ClusterInfo, UserProfile.uid == ClusterInfo.creator_uid)
            .join(ClusterCore, ClusterCore.cid == ClusterInfo.cid)
            .where(ClusterCore.cid == cid)
        )
        return session.exec(statement).first()

    @staticmethod
    def list_cluster_moderators(session: Session, cid: UUID):
        """
        Lists all users holding explicitly assigned moderator roles in the cluster.
        Maps to: LIST ALL MODERATORS OF A CLUSTER
        """
        statement = (
            select(UserProfile.uid, UserProfile.name, ClusterModerator.assigned_at)
            .join(ClusterModerator, UserProfile.uid == ClusterModerator.uid)
            .where(ClusterModerator.cid == cid)
        )
        return session.exec(statement).all()

    @staticmethod
    def check_user_membership(session: Session, cid: UUID, uid: UUID):
        """
        Checks if a specific user possesses membership in a specific cluster.
        Maps to: CHECK IF A USER IS A MEMBER OF A CLUSTER
        """
        statement = select(ClusterMember).where(ClusterMember.cid == cid, ClusterMember.uid == uid)
        return session.exec(statement).first()

    @staticmethod
    def list_cluster_members(session: Session, cid: UUID, limit: int = 50):
        """
        Lists baseline membership representations.
        Maps to: LIST ALL MEMBERS
        """
        statement = (
            select(UserProfile.name, ClusterMember.joined_at, ClusterMember.role)
            .join(ClusterMember, UserProfile.uid == ClusterMember.uid)
            .where(ClusterMember.cid == cid)
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_clusters_by_members(session: Session, limit: int = 5):
        """
        Analytical ranking of clusters by maximum population.
        Maps to: TOP 5 CLUSTERS BY MEMBER COUNT
        """
        statement = (
            select(ClusterCore.name, ClusterStats.member_count)
            .join(ClusterStats, ClusterCore.cid == ClusterStats.cid)
            .order_by(desc(ClusterStats.member_count))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_active_clusters(session: Session, limit: int = 5):
        """
        Analytical ranking of clusters by maximum content creation volume.
        Maps to: TOP 5 ACTIVE CLUSTERS BY POST COUNT
        """
        statement = (
            select(ClusterCore.name, func.count(PostCore.pid).label("post_count"))
            .join(PostCore, ClusterCore.cid == PostCore.cid)
            .group_by(ClusterCore.cid, ClusterCore.name)
            .order_by(desc("post_count"))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_categories(session: Session, limit: int = 5):
        """
        Analytical ranking of system categories by how many clusters represent them.
        Maps to: TOP 5 CATEGORIES BY TOTAL CLUSTERS
        """
        statement = (
            select(ClusterCore.category, func.count(ClusterCore.cid).label("cluster_count"))
            .group_by(ClusterCore.category)
            .order_by(desc("cluster_count"))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_cluster_recommendations_for_user(session: Session, uid: UUID, limit: int = 5):
        """
        Suggests new clusters for a user based on the categories of clusters they already joined.
        """
        user_categories_stmt = (
            select(ClusterCore.category)
            .join(ClusterMember, ClusterCore.cid == ClusterMember.cid)
            .where(ClusterMember.uid == uid)
            .where(ClusterCore.category != None)
            .distinct()
        )
        user_categories = session.exec(user_categories_stmt).all()
        
        if not user_categories:
            return ClusterService.get_public_clusters_by_popularity(session, limit)
            
        recommendation_stmt = (
            select(ClusterCore, ClusterStats.member_count)
            .join(ClusterStats, ClusterCore.cid == ClusterStats.cid)
            .where(ClusterCore.category.in_(user_categories))
            .where(~ClusterCore.cid.in_(
                select(ClusterMember.cid).where(ClusterMember.uid == uid)
            ))
            .where(ClusterCore.is_private == False)
            .order_by(desc(ClusterStats.member_count))
            .limit(limit)
        )
        
        return session.exec(recommendation_stmt).all()

    @staticmethod
    def create_cluster(session: Session, cluster_in):
        """
        Instantiates a new cluster architecture (core, info, stats, initial member).
        ClusterStats.member_count is incremented from 0 by trg_increment_member_count
        when the first ClusterMember row is inserted.
        """
        try:
            core_cluster = ClusterCore(
                name         = cluster_in.name,
                category     = cluster_in.category,
                is_private   = cluster_in.is_private,
                profile_icon = cluster_in.profile_icon
            )
            session.add(core_cluster)
            session.flush()

            info = ClusterInfo(
                cid         = core_cluster.cid,
                description = cluster_in.description,
                creator_uid = cluster_in.creator_uid,
                tags        = cluster_in.tags
            )
            session.add(info)

            # Start at 0 — trigger will increment to 1 when member row is inserted
            stats = ClusterStats(cid=core_cluster.cid, member_count=0)
            session.add(stats)
            session.flush()           # persist stats row BEFORE member insert triggers the increment

            member = ClusterMember(
                cid  = core_cluster.cid,
                uid  = cluster_in.creator_uid,
                role = "MODERATOR"
            )
            session.add(member)
            session.commit()
            session.expire_all()      # clear cache so trigger-updated member_count is visible
            session.refresh(core_cluster)
            session.refresh(info)
            stats = session.get(ClusterStats, core_cluster.cid)

            return core_cluster, info, stats
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def delete_cluster(session: Session, cid: UUID):
        """
        Orchestrates the deletion of a cluster and its associative definitions.
        """
        cluster = session.get(ClusterCore, cid)
        if not cluster: return False
        session.delete(cluster)
        session.commit()
        return True

    @staticmethod
    def add_user_to_cluster(
        session: Session,
        cid: UUID,
        uid: UUID,
        role: str = "MEMBER",
        return_created: bool = False,
        max_retries: int = 3,
    ):
        """
        Joins a user to a cluster in an idempotent, concurrency-safe way.
        ClusterStats.member_count is incremented by trg_increment_member_count.

        Returns the member row by default (backward-compatible).
        If return_created=True, returns (member, created) where created indicates
        whether this call inserted a new membership row.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                member = ClusterMember(cid=cid, uid=uid, role=role)
                session.add(member)
                session.commit()
                session.expire_all()
                if return_created:
                    return member, True
                return member
            except IntegrityError:
                # Duplicate (cid, uid) under races is expected and should not 500.
                session.rollback()
                existing = ClusterService.check_user_membership(session, cid, uid)
                if return_created:
                    return existing, False
                return existing
            except OperationalError as exc:
                session.rollback()
                if "database is locked" in str(exc).lower() and attempt < max_retries:
                    # Brief backoff allows the current writer to finish.
                    time.sleep(0.03 * attempt)
                    continue
                raise

    @staticmethod
    def remove_user_from_cluster(session: Session, cid: UUID, uid: UUID):
        """
        Removes a user from a cluster.
        ClusterStats.member_count is decremented by trg_decrement_member_count.
        """
        statement = select(ClusterMember).where(ClusterMember.cid == cid, ClusterMember.uid == uid)
        member = session.exec(statement).first()
        if member:
            session.delete(member)
            session.commit()
            session.expire_all()
            return True
        return False
