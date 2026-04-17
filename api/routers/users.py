from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List, Any
from uuid import UUID

from api.database import get_session
from api.models.user import UserAuth, UserProfile
from api.schemas.user import UserCreate, UserResponse, UserProfileResponse, UserUpdate
from api.services.user_service import UserService
from api.security import (
    create_access_token,
    get_current_uid,
)
from api.auth import create_access_token, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# ---- Auth -------------------------------------------------------------------

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """
    Authenticates a user with email + password and returns a JWT access token.
    The frontend sends `username` as the email field (OAuth2 convention).
    """
    user = UserService.verify_login_credentials(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.uid)})
    return {"access_token": token, "token_type": "bearer"}


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


# ---- Authenticated "me" endpoints ------------------------------------------

@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Returns the authenticated user's own profile.
    """
    statement = select(UserProfile).where(UserProfile.uid == uid)
    profile = session.exec(statement).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/me/profile", response_model=UserProfileResponse)
def update_my_profile(
    update_data: UserUpdate,
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Partially updates the authenticated user's profile.
    """
    updated = UserService.update_user_profile(session, uid, update_data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated


@router.delete("/me/account")
def delete_my_account(
    uid: UUID = Depends(get_current_uid),
    session: Session = Depends(get_session),
):
    """
    Permanently deletes the authenticated user's account and profile.
    """
    # Delete profile first (FK dependency), then the auth record
    profile = session.get(UserProfile, uid)
    if profile:
        session.delete(profile)
    
    success = UserService.delete_user_account(session, uid)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted successfully"}


# ---- Global stat endpoints (path must come BEFORE /{uid}) -------------------

@router.get("/stats/most-active-verified")
def most_active_verified(limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns the most prolific verified users ranked by post count.
    """
    rows = UserService.get_most_active_verified_users(session, limit)
    return [{"uid": str(r[0]), "post_count": r[1]} for r in rows]


@router.get("/stats/most-liked")
def most_liked(limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns users ranked by aggregate likes across all their posts.
    """
    rows = UserService.get_most_liked_users(session, limit)
    return [{"uid": str(r[0]), "total_likes": r[1], "post_count": r[2]} for r in rows]


@router.get("/stats/most-engaged")
def most_engaged(limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns users ranked by total reactions they have left on posts.
    """
    rows = UserService.get_most_engaged_users(session, limit)
    return [{"uid": str(r[0]), "reaction_count": r[1]} for r in rows]


# ---- Public user endpoints --------------------------------------------------

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
    profiles = session.exec(statement).all()
    return profiles


# ---- Per-user analytics endpoints -------------------------------------------

@router.get("/{uid}/posts")
def user_posts(uid: UUID, session: Session = Depends(get_session)):
    """
    Lists all posts authored by a specific user across every cluster.
    """
    rows = UserService.get_user_posts_across_clusters(session, uid)
    return [
        {
            "uid": str(r[0]),
            "content": r[1],
            "tags": r[2],
            "created_at": str(r[3]),
            "cid": str(r[4]),
        }
        for r in rows
    ]


@router.get("/{uid}/post-distribution")
def user_post_distribution(uid: UUID, session: Session = Depends(get_session)):
    """
    Returns how many posts a user has created per cluster.
    """
    rows = UserService.get_user_post_distribution(session, uid)
    return [
        {
            "uid": str(r[0]),
            "cluster_name": r[1],
            "post_count": r[2],
        }
        for r in rows
    ]


@router.get("/{uid}/top-posts")
def user_top_posts(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns the most liked posts by a user.
    """
    rows = UserService.get_top_posts_by_user(session, uid, limit)
    return [{"uid": str(r[0]), "content": r[1], "likes": r[2]} for r in rows]


@router.get("/{uid}/top-comments")
def user_top_comments(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns the most liked comments by a user.
    """
    rows = UserService.get_top_comments_by_user(session, uid, limit)
    return [{"uid": str(r[0]), "content": r[1], "likes": r[2]} for r in rows]


@router.get("/{uid}/most-disliked-posts")
def user_most_disliked_posts(uid: UUID, limit: int = 5, session: Session = Depends(get_session)):
    """
    Returns the most disliked posts by a user.
    """
    rows = UserService.get_most_disliked_posts_by_user(session, uid, limit)
    return [{"uid": str(r[0]), "content": r[1], "dislikes": r[2]} for r in rows]
