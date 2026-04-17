from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class UserFollow(SQLModel, table=True):
    """
    Directed follow edge: follower_uid follows following_uid.
    """
    __table_args__ = {"extend_existing": True}

    follower_uid: UUID = Field(foreign_key="userauth.uid", primary_key=True, index=True)
    following_uid: UUID = Field(foreign_key="userauth.uid", primary_key=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
