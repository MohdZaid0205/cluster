import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlmodel import Session, select
from uuid import UUID

from api.database import get_session
from api.models.user import UserAuth
from api.security import verify_password

# Authentication settings
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# The tokenUrl matches the login route we will add
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")
optional_http_bearer = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT access token encoding the given data.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> UserAuth:
    """
    Dependency that extracts the current user from the JWT token in the request header.
    Validates the token and fetches the UserAuth record from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid_str: str = payload.get("sub")
        if uid_str is None:
            raise credentials_exception
        token_data = UUID(uid_str)
    except jwt.PyJWTError:
        raise credentials_exception
        
    statement = select(UserAuth).where(UserAuth.uid == token_data)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(optional_http_bearer)],
    session: Session = Depends(get_session),
) -> Optional[UserAuth]:
    """
    Returns the authenticated user when Authorization Bearer is valid; otherwise None.
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        uid_str: Optional[str] = payload.get("sub")
        if uid_str is None:
            return None
        token_data = UUID(uid_str)
    except jwt.PyJWTError:
        return None
    user = session.exec(select(UserAuth).where(UserAuth.uid == token_data)).first()
    return user
