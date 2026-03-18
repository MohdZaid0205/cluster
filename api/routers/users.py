from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List, Any
from uuid import UUID

from api.database import get_session
from api.models.user import UserAuth, UserProfile
from api.schemas.user import UserCreate, UserResponse, UserProfileResponse, UserUpdate
from api.services.user_service import UserService
from api.auth import create_access_token, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

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

@router.get("/{uid}/posts", response_model=List[Any])
def get_user_posts(uid: UUID, session: Session = Depends(get_session)):
    """
    Lists all content authored by a specific user system-wide.
    """
    return UserService.get_user_posts_across_clusters(session, uid)

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
