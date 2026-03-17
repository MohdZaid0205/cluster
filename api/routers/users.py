from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from api.database import get_session
from api.models.user import UserAuth, UserProfile
from api.schemas.user import UserCreate, UserResponse, UserProfileResponse, UserUpdate
from api.services.user_service import UserService

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
