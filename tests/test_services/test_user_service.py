import pytest
from uuid import uuid4
from sqlmodel import Session
from api.services.user_service import UserService
from api.models.user import UserRole
from api.security import get_password_hash

def test_verify_login_credentials(session: Session, test_user, test_password):
    # Success case
    user = UserService.verify_login_credentials(session, "test@example.com", test_password)
    assert user is not None
    assert user.uid == test_user.uid

    # Failure cases
    assert UserService.verify_login_credentials(session, "test@example.com", "wrong_password") is None
    assert UserService.verify_login_credentials(session, "not_found@example.com", test_password) is None

def test_get_user_profile_stats_success(session: Session, test_user, test_password):
    profile = UserService.get_user_profile_stats(session, test_user.email, test_password)
    assert profile is not None
    assert profile.name == "Test User"
    assert profile.bio == "I am a test user."

def test_get_user_profile_stats_failure(session: Session, test_user):
    profile = UserService.get_user_profile_stats(session, test_user.email, "wrong_password")
    assert profile is None

def test_verify_user_account(session: Session, test_user):
    assert test_user.is_verified is True
    
    # Let's create an unverified user
    from api.models.user import UserAuth
    unverified_uid = uuid4()
    unverified_user = UserAuth(
        uid=unverified_uid,
        email="unverified@example.com",
        password_hash=get_password_hash("pass"),
        role=UserRole.MEMBER,
        is_verified=False
    )
    session.add(unverified_user)
    session.commit()

    success = UserService.verify_user_account(session, unverified_uid, "new_email@example.com")
    
    # Check if updated
    assert success is True
    updated_user = session.get(UserAuth, unverified_uid)
    assert updated_user.is_verified is True
    assert updated_user.email == "new_email@example.com"

def test_update_user_profile(session: Session, test_user):
    update_data = {
        "name": "Updated Name",
        "location": "Updated Location"
    }
    
    updated_profile = UserService.update_user_profile(session, test_user.uid, update_data)
    
    assert updated_profile is not None
    assert updated_profile.name == "Updated Name"
    assert updated_profile.location == "Updated Location"
    assert updated_profile.bio == "I am a test user." # Unchanged
    
def test_delete_user_account(session: Session, test_user):
    # Ensure exists
    from api.models.user import UserAuth, UserProfile
    assert session.get(UserAuth, test_user.uid) is not None
    
    # Delete
    success = UserService.delete_user_account(session, test_user.uid)
    assert success is True
    
    # Check deletion (profile cascade isn't fully set up in the DB schema provided so we just check auth)
    assert session.get(UserAuth, test_user.uid) is None
    
