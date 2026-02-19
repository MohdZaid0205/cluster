
import os
import random
import time
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, create_engine, Session, select
from faker import Faker

# --- Setup ---
os.makedirs("archive/research", exist_ok=True)
os.makedirs("temp/db", exist_ok=True)
DATABASE_URL = "sqlite:///temp/db/research.db"
engine = create_engine(DATABASE_URL, echo=False)
fake = Faker()

# --- Enums ---
class UserRole(str, Enum):
    GUEST = "GUEST"
    MEMBER = "MEMBER"
    VERIFIED = "VERIFIED"
    ADMIN = "ADMIN"

class ClusterRole(str, Enum):
    MEMBER = "MEMBER"
    MODERATOR = "MODERATOR"

class PostType(str, Enum):
    TEXT = "TEXT"
    LINK = "LINK"
    WINDOW = "WINDOW"

class ReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    LOVE = "LOVE"

class MegaphoneType(str, Enum):
    ANNOUNCEMENT = "ANNOUNCEMENT"
    POLL = "POLL"
    EVENT = "EVENT"

class RuleAction(str, Enum):
    BLOCK = "BLOCK"
    FLAG = "FLAG"

# --- Schema Definitions (Fragmented) ---

# 1. User
class UserAuth(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    email: Optional[str] = Field(default=None, index=True, sa_column_kwargs={"unique": True})
    phone: Optional[str] = Field(default=None, index=True, sa_column_kwargs={"unique": True})
    password_hash: str
    role: UserRole = Field(default=UserRole.MEMBER)
    is_verified: bool = Field(default=False)

class UserProfile(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    profile_image: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

# 2. Cluster
class ClusterCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    category: Optional[str] = Field(default=None, index=True)
    is_private: bool = Field(default=False)
    profile_icon: Optional[str] = None

class ClusterInfo(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    description: Optional[str] = None
    creator_uid: UUID = Field(foreign_key="userauth.uid") # Link to UserAuth or Profile
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: Optional[str] = None

class ClusterStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    member_count: int = 0

# Cluster Relations
class ClusterMember(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    role: ClusterRole = Field(default=ClusterRole.MEMBER)

class ClusterModerator(SQLModel, table=True):
    """Audit/Specific table for moderators as requested"""
    __table_args__ = {"extend_existing": True}
    cid: UUID = Field(primary_key=True, foreign_key="clustercore.cid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class ClusterRule(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    rid: UUID = Field(default_factory=uuid4, primary_key=True)
    cid: UUID = Field(index=True, foreign_key="clustercore.cid")
    name: str
    pattern: str
    action: RuleAction
    description: Optional[str] = None

# 3. Post
class PostCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(default_factory=uuid4, primary_key=True)
    uid: UUID = Field(index=True, foreign_key="userauth.uid")
    cid: UUID = Field(index=True, foreign_key="clustercore.cid")
    type: PostType = Field(default=PostType.TEXT)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = None

class PostContent(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    content: str
    tags: Optional[str] = None

class PostStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    likes: int = 0
    dislikes: int = 0

# Post Relations
class PostReaction(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    reaction_type: ReactionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Window(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    wid: UUID = Field(primary_key=True, foreign_key="postcore.pid") # It IS a post?
    origin_pid: UUID = Field(foreign_key="postcore.pid")
    shared_by_uid: UUID = Field(foreign_key="userauth.uid")
    shared_into_cid: UUID = Field(foreign_key="clustercore.cid")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Megaphone(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    pid: UUID = Field(primary_key=True, foreign_key="postcore.pid")
    start_time: datetime
    end_time: datetime
    type: MegaphoneType
    is_active: bool = True
    subscriber_count: int = 0

# 4. Comment
class CommentCore(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(default_factory=uuid4, primary_key=True)
    uid: UUID = Field(foreign_key="userauth.uid")
    pid: Optional[UUID] = Field(default=None,  index=True, foreign_key="postcore.pid") # Root comment
    parent_mid: Optional[UUID] = Field(default=None, index=True, foreign_key="commentcore.mid") # Reply
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class CommentContent(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    content: str

class CommentStats(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    likes: int = 0
    dislikes: int = 0

class CommentReaction(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    mid: UUID = Field(primary_key=True, foreign_key="commentcore.mid")
    uid: UUID = Field(primary_key=True, foreign_key="userauth.uid")
    reaction_type: ReactionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Generation Logic ---



def populate_users(n=1000):
    print(f"Generating {n} Users...")
    users = []
    profiles = []
    user_ids = []
    poster_ids = []
    
    for _ in range(n):
        # Generate UID explicitly to ensure we have it safe
        uid = uuid4()
        role = random.choices([UserRole.MEMBER, UserRole.VERIFIED, UserRole.ADMIN], weights=[0.8, 0.15, 0.05])[0]
        is_verified = role == UserRole.VERIFIED or role == UserRole.ADMIN
        
        use_email = random.choice([True, False])
        email = fake.unique.email() if use_email else None
        phone = fake.unique.phone_number() if not use_email else (fake.unique.phone_number() if random.random() > 0.5 else None)
        
        auth = UserAuth(
            uid=uid,
            email=email,
            phone=phone,
            password_hash=fake.sha256(),
            role=role,
            is_verified=is_verified
        )
        users.append(auth)
        user_ids.append(uid)
        
        if is_verified or email is not None or phone is not None:
            poster_ids.append(uid)
        
        profile = UserProfile(
            uid=uid,
            name=fake.name(),
            bio=fake.sentence() if random.random() > 0.2 else None,
            location=fake.city() if random.random() > 0.3 else None,
            profile_image=fake.image_url() if random.random() > 0.1 else None,
            created_at=fake.date_time_this_year(),
            last_active=fake.date_time_this_year()
        )
        profiles.append(profile)
    

    with Session(engine) as session:
        for i in range(0, len(users), 1000):
            session.add_all(users[i:i+1000])
            session.add_all(profiles[i:i+1000])
            session.commit()
            
    return user_ids, poster_ids



def populate_clusters(user_ids, n=100):
    print(f"Generating {n} Clusters...")
    core_list = []
    info_list = []
    stats_list = []
    
    all_cids = []
    
    # 1. Create Clusters
    for _ in range(n):
        cid = uuid4()
        creator = random.choice(user_ids) # Any user can create/join for now
        core = ClusterCore(
            cid=cid,
            name=fake.company(),
            category=random.choice(["Tech", "Art", "News", "Gaming", "Music", "Science"]), 
            is_private=random.choice([True, False]),
            profile_icon=fake.image_url()
        )
        core_list.append(core)
        all_cids.append(cid)
        
        info = ClusterInfo(
            cid=cid,
            description=fake.text(),
            creator_uid=creator,
            created_at=fake.date_time_this_year(),
            tags=fake.word()
        )
        info_list.append(info)
        
        stats = ClusterStats(cid=cid, member_count=1)
        stats_list.append(stats)
        
    with Session(engine) as session:
        for i in range(0, len(core_list), 1000):
            session.add_all(core_list[i:i+1000])
            session.add_all(info_list[i:i+1000])
            session.add_all(stats_list[i:i+1000])
            session.commit()
            
    # 2. Assign Membership with Outliers (Pareto-ish)
    print(f"Generating Relations for Clusters (Outlier Distribution)...")
    
    # Distribution:
    # 20% users = 0 clusters (Isolates)
    # 70% users = 1-5 clusters (Normies)
    # 10% users = 10-50 clusters (Connectors/Super-users)
    
    cluster_memberships = []
    cluster_moderators = []
    
    shuffled_users = list(user_ids)
    random.shuffle(shuffled_users)
    
    isolates_count = int(len(user_ids) * 0.2)
    normies_count = int(len(user_ids) * 0.7)
    connectors_count = len(user_ids) - isolates_count - normies_count
    
    # Isolates (First 20%) -> Do nothing
    
    # Normies (Next 70%)
    normies = shuffled_users[isolates_count : isolates_count + normies_count]
    for uid in normies:
        # Join 1-5 clusters
        target_clusters = random.sample(all_cids, k=random.randint(1, 5))
        for cid in target_clusters:
            cluster_memberships.append(ClusterMember(cid=cid, uid=uid, joined_at=fake.date_time_this_year()))
    
    # Connectors (Last 10%)
    connectors = shuffled_users[isolates_count + normies_count :]
    for uid in connectors:
        # Join 10-50 clusters
        target_clusters = random.sample(all_cids, k=random.randint(10, 50))
        for cid in target_clusters:
            cluster_memberships.append(ClusterMember(cid=cid, uid=uid, joined_at=fake.date_time_this_year()))
            # Higher chance to be mod
            if random.random() < 0.2:
                cluster_memberships[-1].role = ClusterRole.MODERATOR
                cluster_moderators.append(ClusterModerator(cid=cid, uid=uid))


    # 3. Add Rules (Cluster-centric)
    cluster_rules = []
    for cid in all_cids:
        for _ in range(random.randint(1, 5)):
            cluster_rules.append(ClusterRule(cid=cid, name=fake.word(), pattern="regex", action=random.choice(list(RuleAction))))

    with Session(engine) as session:
        # Batch add rules
        for i in range(0, len(cluster_rules), 1000):
            session.add_all(cluster_rules[i:i+1000])
        # Batch add members
        for i in range(0, len(cluster_memberships), 1000):
            session.add_all(cluster_memberships[i:i+1000])
        # Batch add mods
        for i in range(0, len(cluster_moderators), 1000):
            session.add_all(cluster_moderators[i:i+1000])
        session.commit()
        
    return all_cids

def populate_posts(user_ids, cluster_ids, n=10000):
    print(f"Generating {n} Posts (Outlier Distribution)...")
    # user_ids here should be the 'poster_ids' subset
    posts_core = []
    posts_content = []
    posts_stats = []
    post_ids = []
    
    # Distribution:
    # 1% Power Users create 50% of posts
    # 19% Active Users create 50% of posts
    # 80% Lurkers create 0 posts
    
    if not user_ids:
        print("Warning: No eligible posters found!")
        return []
        
    power_user_count = max(1, int(len(user_ids) * 0.01))
    active_user_count = max(1, int(len(user_ids) * 0.19))
    
    shuffled_users = list(user_ids)
    random.shuffle(shuffled_users)
    
    power_users = shuffled_users[:power_user_count]
    active_users = shuffled_users[power_user_count : power_user_count + active_user_count]
    # Lurkers = Rest
    
    # Safety check for division
    posts_per_power_user = int((n * 0.5) / len(power_users)) if power_users else 0
    posts_per_active_user = int((n * 0.5) / len(active_users)) if active_users else 0
    
    # Helper to generate a post
    def create_post_obj(uid):
        pid = uuid4()
        cid = random.choice(cluster_ids) # In reality, should be a cluster they joined, but random is okay for PoC
        ptype = random.choice(list(PostType))
        
        core = PostCore(pid=pid, uid=uid, cid=cid, type=ptype, created_at=fake.date_time_this_year())
        posts_core.append(core)
        post_ids.append(pid)
        
        content = PostContent(pid=pid, content=fake.text(), tags=fake.word())
        posts_content.append(content)
        
        stats = PostStats(pid=pid, likes=random.randint(0, 100))
        posts_stats.append(stats)

    # Generate Power User Posts
    for uid in power_users:
        for _ in range(posts_per_power_user):
            create_post_obj(uid)
            
    # Generate Active User Posts
    for uid in active_users:
        for _ in range(posts_per_active_user):
            create_post_obj(uid)
            
    # Fill remainder (rounding errors) with random active users
    current_count = len(posts_core)
    while current_count < n:
        uid = random.choice(active_users) if active_users else random.choice(user_ids)
        create_post_obj(uid)
        current_count += 1
        
    with Session(engine) as session:
         for i in range(0, len(posts_core), 1000):
            session.add_all(posts_core[i:i+1000])
            session.add_all(posts_content[i:i+1000])
            session.add_all(posts_stats[i:i+1000])
            session.commit()
            
    return post_ids


def populate_reactions(user_ids, post_ids, comment_ids):
    print(f"Generating Reactions...")
    with Session(engine) as session:
        # Post Reactions
        # 10% of posts get reactions
        target_posts = random.sample(post_ids, k=int(len(post_ids) * 0.1))
        for pid in target_posts:
            # Random users react (Anyone can react)
            reactors = random.sample(user_ids, k=random.randint(1, 10))
            for uid in reactors:
                reaction = PostReaction(
                    pid=pid,
                    uid=uid,
                    reaction_type=random.choice(list(ReactionType)),
                    timestamp=fake.date_time_this_year()
                )
                session.add(reaction)
        
        # Comment Reactions
        # 5% of comments get reactions
        if comment_ids:
            target_comments = random.sample(comment_ids, k=int(len(comment_ids) * 0.05))
            for mid in target_comments:
                reactors = random.sample(user_ids, k=random.randint(1, 5))
                for uid in reactors:
                    reaction = CommentReaction(
                        mid=mid,
                        uid=uid,
                        reaction_type=random.choice(list(ReactionType)),
                        timestamp=fake.date_time_this_year()
                    )
                    session.add(reaction)
        
        session.commit()

def populate_special_features(user_ids, cluster_ids, post_ids):
    print("Generating Windows and Megaphones...")
    with Session(engine) as session:
        # Windows (Shares)
        # Create new "Window" posts that share existing posts
        # We need to create PostCore entries for them first as per schema (Window PK is foreign key to Post)
        # Only capable posters should share/window
        
        # Share 1000 posts
        users_to_share = random.choices(user_ids, k=1000)
        posts_to_share = random.choices(post_ids, k=1000)
        clusters_to_share_into = random.choices(cluster_ids, k=1000)
        
        for i in range(1000):
            # 1. Create the PostCore for the Window
            uid = users_to_share[i]
            cid = clusters_to_share_into[i]
            origin_pid = posts_to_share[i]
            
            window_post = PostCore(
                uid=uid,
                cid=cid,
                type=PostType.WINDOW,
                created_at=fake.date_time_this_year()
            )
            session.add(window_post)
            session.flush() # Get PID
            
            # 2. Create Window entry
            window = Window(
                wid=window_post.pid,
                origin_pid=origin_pid,
                shared_by_uid=uid,
                shared_into_cid=cid,
                created_at=window_post.created_at
            )
            session.add(window)
            
        # Megaphones
        # Turn random EXISTING posts into Megaphones (or create new ones, but let's upgrade existing for now or just new ones)
        # Let's create NEW megaphone posts
        for _ in range(50): # 50 active megaphones
            uid = random.choice(user_ids)
            cid = random.choice(cluster_ids)
            
            mega_post = PostCore(
                uid=uid,
                cid=cid,
                type=PostType.TEXT, # Underlying type
                created_at=fake.date_time_this_year()
            )
            session.add(mega_post)
            session.flush()
            
            mega = Megaphone(
                pid=mega_post.pid,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(days=7),
                type=random.choice(list(MegaphoneType)),
                is_active=True,
                subscriber_count=random.randint(0, 500)
            )
            session.add(mega)
            
        session.commit()

def main():
    print("Initializing Database...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    # Scale for PoC
    N_USERS = 10_000
    N_CLUSTERS = 500
    N_POSTS = 100_000
    
    start = time.time()
    
    # populate_users now returns tuple
    user_ids, poster_ids = populate_users(N_USERS)
    print(f"Eligible Posters: {len(poster_ids)} / {N_USERS}")
    

    # Only eligible posters can create/join clusters
    cluster_ids = populate_clusters(poster_ids, N_CLUSTERS)
    
    # Use poster_ids for generating content (Posts)
    post_ids = populate_posts(poster_ids, cluster_ids, N_POSTS)
    
    # Comments
    print("Generating Comments...")
    comment_ids = []
    with Session(engine) as session:
        # Generate comments for first 5000 posts (to keep speed reasonable)
        target_posts = post_ids[:5000]
        for pid in target_posts:
            for _ in range(random.randint(1, 5)):
                # Lurkers CAN comment (User Report 1)
                uid = random.choice(user_ids)
                core = CommentCore(uid=uid, pid=pid)
                session.add(core)
                session.add(CommentContent(mid=core.mid, content=fake.sentence()))
                session.add(CommentStats(mid=core.mid))
                comment_ids.append(core.mid) # Capture for reactions
        session.commit()
    
    # NEW: Populate Relations
    # Reactions can come from lurkers (all users)
    populate_reactions(user_ids, post_ids, comment_ids)
    
    # Windows/Megaphones should probably come from posters
    populate_special_features(poster_ids, cluster_ids, post_ids)
        
    print(f"Done! Created {N_USERS} Users, {N_CLUSTERS} Clusters, {N_POSTS} Posts + Relations in {time.time()-start:.2f}s")




if __name__ == "__main__":
    main()
