from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from api.models.enums import UserRole

class UserCreate(BaseModel):
    """
    Schema for validating the creation of a new user account.
    """
    name    : str                                                              # Full display name of the user
    password: str                                                              # Plain text password (to be securely hashed)
    email   : Optional[EmailStr] = None                                        # Optional email for contact and login
    phone   : Optional[str]      = None                                        # Optional phone number for contact and login
    role    : Optional[UserRole] = UserRole.MEMBER                             # User role assignment, defaults to MEMBER
    bio     : Optional[str]      = None                                        # Initial biography text for the profile
    location: Optional[str]      = None                                        # Initial location string for the profile

class UserUpdate(BaseModel):
    """
    Schema for validating partial updates to an existing user's profile.
    """
    name         : Optional[str] = None                                        # Updated display name
    bio          : Optional[str] = None                                        # Updated biography text
    location     : Optional[str] = None                                        # Updated geographical location
    profile_image: Optional[str] = None                                        # Updated URL to profile image

class UserResponse(BaseModel):
    """
    Schema representing the core system data returned for a specific user.
    """
    uid        : UUID                                                          # Global unique identity of the user
    email      : Optional[str]   = None                                        # Email address assigned to the user
    phone      : Optional[str]   = None                                        # Contact phone number
    role       : UserRole                                                      # Actual active system role
    is_verified: bool                                                          # Tells whether the user's primary contact is verified

class UserProfileResponse(BaseModel):
    """
    Schema mapping to the public profile representation of a user.
    """
    uid          : UUID                                                        # Global unique identity of the user
    name         : str                                                         # The display name of the user
    bio          : Optional[str] = None                                        # The current biography text
    location     : Optional[str] = None                                        # The current location text
    profile_image: Optional[str] = None                                        # Image URL for the profile picture
    created_at   : datetime                                                    # Account creation timestamp
    last_active  : datetime                                                    # Most recent known interaction time
