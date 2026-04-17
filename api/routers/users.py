from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List, Any
from uuid import UUID

from api.database import get_session
from api.models.user import UserAuth, UserProfile
from api.models.post import PostCore, PostContent, PostStats
from api.models.comment import CommentCore, CommentContent, CommentStats
from api.schemas.user import UserCreate, UserResponse, UserProfileResponse, UserUpdate
from api.services.user_service import UserService
from api.auth import create_access_token, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# In-memory follow store (quick functional implementation without adding a new DB table)
_follows: dict[str, set[str]] = {}    # target_uid -> set of follower_uids (who follows this user)
_following: dict[str, set[str]] = {}  # follower_uid -> set of followed_uids (who this user follows)

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, session: Session = Depends(get_session)):
    """
    Registers a new user setting up their authentication credentials and public profile.
    """
    if user_in.email:
        statement = select(UserAuth).where(UserAuth.email == user_in.email)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

    auth_user, profile = UserService.register_user(session, user_in)
    return auth_user

# ---- Static-path endpoints MUST come before /{uid} dynamic routes ------------

@router.get("/search", response_model=List[UserProfileResponse])
def search_users(q: str = "", limit: int = 20, session: Session = Depends(get_session)):
    """
    Searches users by name (case-insensitive substring match).
    """
    if not q.strip():
        statement = select(UserProfile).limit(limit)
    else:
        statement = select(UserProfile).where(
            UserProfile.name.ilike(f"%{q}%")
        ).limit(limit)
    return session.exec(statement).all()

@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Retrieves the public profile for the currently authenticated user.
    """
    statement = select(UserProfile).where(UserProfile.uid == current_user.uid)
    profile = session.exec(statement).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.patch("/me/profile", response_model=UserProfileResponse)
def update_my_profile(update_data: UserUpdate, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Updates the authenticated user's profile.
    """
    updated_profile = UserService.update_user_profile(session, current_user.uid, update_data.model_dump(exclude_unset=True))
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated_profile

@router.delete("/me/account")
def delete_my_account(session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Deletes the authenticated user's account completely.
    """
    success = UserService.delete_user_account(session, current_user.uid)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account successfully deleted"}

@router.post("/me/verify")
def verify_my_account(new_email: str, session: Session = Depends(get_session), current_user: UserAuth = Depends(get_current_user)):
    """
    Simulates account verification and updating email.
    """
    UserService.verify_user_account(session, current_user.uid, new_email)
    return {"message": "Account verified successfully"}

@router.get("/stats/most-active-verified", response_model=List[Any])
def get_most_active_verified(limit: int = 5, session: Session = Depends(get_session)):
    """
    Ranks top verified users based purely on contribution volume (post count).
    """
    return UserService.get_most_active_verified_users(session, limit)

@router.get("/stats/most-liked", response_model=List[Any])
def get_most_liked(limit: int = 5, session: Session = Depends(get_session)):
    """
    Ranks top overall users based on total aggregate likes accumulated across all posts.
    """
    return UserService.get_most_liked_users(session, limit)

@router.get("/stats/most-engaged", response_model=List[Any])
def get_most_engaged(limit: int = 5, session: Session = Depends(get_session)):
    """
    Ranks top users based on how frequently they leave reactions on others' posts.
    """
    return UserService.get_most_engaged_users(session, limit)

# ---- Dynamic /{uid} routes ----------------------------------------------------

@router.get("/{uid}", response_model=UserProfileResponse)
def get_user(uid: UUID, session: Session = Depends(get_session)):
    """
    Retrieves the public profile for a specific user ID.
    """
    statement = select(UserProfile).where(UserProfile.uid == uid)
    profile = session.exec(statement).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile

@router.get("/", response_model=List[UserProfileResponse])
def list_users(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """
    Returns a paginated list of all user profiles.
    """
    statement = select(UserProfile).offset(skip).limit(limit)
    return session.exec(statement).all()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """
    Authenticates a user and returns a JWT token.
    """
    user = UserService.verify_login_credentials(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.uid)})
    return {"access_token": access_token, "token_type": "bearer"}

# ---- Follow / Unfollow --------------------------------------------------------

@router.get("/{uid}/follow/me", response_model=Any)
def check_follow_status(uid: UUID, current_user: UserAuth = Depends(get_current_user)):
    """
    Returns whether the current user follows the target user.
    """
    followers = _follows.get(str(uid), set())
    return {"is_following": str(current_user.uid) in followers, "follower_count": len(followers)}

@router.post("/{uid}/follow")
def follow_user(uid: UUID, current_user: UserAuth = Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Follows a user. Idempotent.
    """
    if str(uid) == str(current_user.uid):
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    profile = session.exec(select(UserProfile).where(UserProfile.uid == uid)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    _follows.setdefault(str(uid), set()).add(str(current_user.uid))
    _following.setdefault(str(current_user.uid), set()).add(str(uid))
    return {"message": "Followed", "follower_count": len(_follows[str(uid)])}

@router.delete("/{uid}/follow")
def unfollow_user(uid: UUID, current_user: UserAuth = Depends(get_current_user)):
    """
    Unfollows a user. Idempotent.
    """
    _follows.setdefault(str(uid), set()).discard(str(current_user.uid))
    _following.setdefault(str(current_user.uid), set()).discard(str(uid))
    return {"message": "Unfollowed", "follower_count": len(_follows.get(str(uid), set()))}

@router.get("/{uid}/followers", response_model=Any)
def get_followers(uid: UUID, session: Session = Depends(get_session)):
    """
    Returns the list of users who follow the given uid.
    """
    follower_uids = list(_follows.get(str(uid), set()))
    profiles = []
    for fuid in follower_uids:
        try:
            p = session.exec(select(UserProfile).where(UserProfile.uid == fuid)).first()
            if p:
                profiles.append({"uid": str(p.uid), "name": p.name, "bio": p.bio})
        except Exception:
            pass
    return profiles

@router.get("/{uid}/following", response_model=Any)
def get_following(uid: UUID, session: Session = Depends(get_session)):
    """
    Returns the list of users the given uid follows.
    """
    following_uids = list(_following.get(str(uid), set()))
    profiles = []
    for fuid in following_uids:
        try:
            p = session.exec(select(UserProfile).where(UserProfile.uid == fuid)).first()
            if p:
                profiles.append({"uid": str(p.uid), "name": p.name, "bio": p.bio})
        except Exception:
            pass
    return profiles

# ---- Public user data ---------------------------------------------------------

@router.get("/{uid}/posts", response_model=List[Any])
def get_user_posts(uid: UUID, session: Session = Depends(get_session)):
    """
    Lists all content authored by a specific user system-wide.
    """
    return UserService.get_user_posts_across_clusters(session, uid)

@router.get("/{uid}/recent-posts", response_model=List[Any])
def get_user_recent_posts(uid: UUID, limit: int = 30, session: Session = Depends(get_session)):
    """
    Returns recent posts by a user in full PostResponse shape.
    """
    statement = (
        select(PostCore, PostContent, PostStats)
        .join(PostContent, PostCore.pid == PostContent.pid)
        .join(PostStats, PostCore.pid == PostStats.pid)
        .where(PostCore.uid == uid)
        .order_by(PostCore.created_at.desc())
        .limit(limit)
    )
    results = session.exec(statement).all()
    return [
        {
            "pid": core.pid, "uid": core.uid, "cid": core.cid,
            "type": core.type, "content": content.content,
            "tags": content.tags, "created_at": core.created_at,
            "likes": stats.likes, "dislikes": stats.dislikes,
        }
        for core, content, stats in results
    ]

@router.get("/{uid}/recent-comments", response_model=List[Any])
def get_user_recent_comments(uid: UUID, limit: int = 30, session: Session = Depends(get_session)):
    """
    Returns recent comments by a user.
    """
    statement = (
        select(CommentCore, CommentContent, CommentStats)
        .join(CommentContent, CommentCore.mid == CommentContent.mid)
        .join(CommentStats, CommentCore.mid == CommentStats.mid)
        .where(CommentCore.uid == uid)
        .order_by(CommentCore.created_at.desc())
        .limit(limit)
    )
    results = session.exec(statement).all()
    return [
        {
            "mid": core.mid, "uid": core.uid, "pid": core.pid,
            "parent_mid": core.parent_mid, "content": content.content,
            "created_at": core.created_at, "likes": stats.likes, "dislikes": stats.dislikes,
        }
        for core, content, stats in results
    ]

@router.get("/{uid}/post-distribution", response_model=List[Any])
def get_user_post_distribution(uid: UUID, session: Session = Depends(get_session)):
    """
    Analyzes a user's posting behavior across multiple clusters.
    """
    return UserService.get_user_post_distribution(session, uid)

@router.get("/{uid}/top-comments", response_model=List[Any])
def get_top_comments(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Retrieves the most liked comments ever made by a user.
    """
    return UserService.get_top_comments_by_user(session, uid, limit)

@router.get("/{uid}/top-posts", response_model=List[Any])
def get_top_posts(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Retrieves the most positively received posts authored by a user.
    """
    return UserService.get_top_posts_by_user(session, uid, limit)

@router.get("/{uid}/most-disliked-posts", response_model=List[Any])
def get_most_disliked_posts(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Retrieves the most negatively received posts authored by a user.
    """
    return UserService.get_most_disliked_posts_by_user(session, uid, limit)
