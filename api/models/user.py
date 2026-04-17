from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime
from sqlmodel import Field, SQLModel
from api.models.enums import UserRole

class UserAuth(SQLModel, table=True):
    """
    Represents the authentication credentials and core identity for a user.
    """
    __table_args__ = {"extend_existing": True}

    uid          : UUID           = Field(default_factory=uuid4, primary_key=True)  # Unique identifier for the user
    email        : Optional[str]  = Field(default=None, index=True, sa_column_kwargs={"unique": True}) # User's email address
    phone        : Optional[str]  = Field(default=None, index=True, sa_column_kwargs={"unique": True}) # User's phone number
    password_hash: str                                                              # Hashed password for authentication
    role         : UserRole       = Field(default=UserRole.MEMBER)                  # System role assigned to the user
    is_verified  : bool           = Field(default=False)                            # Indicates if the account is verified

class UserProfile(SQLModel, table=True):
    """
    Contains the public profile information and display settings for a user.
    """
    __table_args__ = {"extend_existing": True}

    uid          : UUID           = Field(primary_key=True, foreign_key="userauth.uid") # Foreign key linked to UserAuth
    name         : str                                                                  # Display name of the user
    bio          : Optional[str]  = None                                                # Short biography or status message
    location     : Optional[str]  = None                                                # Geographical location of the user
    profile_image: Optional[str]  = None                                                # URL to the user's profile image
    created_at   : datetime       = Field(default_factory=lambda: datetime.now(), index=True)      # Timestamp of profile creation
    last_active  : datetime       = Field(default_factory=lambda: datetime.now(), index=True)      # Timestamp of last activity
