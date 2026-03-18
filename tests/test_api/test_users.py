import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlmodel import Session
from api.models.user import UserAuth, UserProfile, UserRole

def test_create_user_success(client: TestClient, session: Session):
    user_data = {
        "name": "New API User",
        "password": "secure_password",
        "email": "apiuser@example.com",
        "bio": "API test user",
        "location": "API City"
    }
    
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert "uid" in data
    assert data["email"] == "apiuser@example.com"
    assert data["role"] == UserRole.MEMBER
    
    # Check DB
    from uuid import UUID
    user = session.get(UserAuth, UUID(data["uid"]))
    assert user is not None
    assert user.email == "apiuser@example.com"

def test_create_user_duplicate_email(client: TestClient, test_user):
    user_data = {
        "name": "Duplicate User",
        "password": "secure_password",
        "email": test_user.email,  # Should conflict
    }
    
    response = client.post("/users/", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_get_user_success(client: TestClient, test_user):
    response = client.get(f"/users/{test_user.uid}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["bio"] == "I am a test user."

def test_get_user_not_found(client: TestClient):
    response = client.get(f"/users/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_list_users(client: TestClient, test_user):
    # Ensure there's at least one user (test_user)
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(u["uid"] == str(test_user.uid) for u in data)

def test_login_success(client: TestClient, test_user, test_password):
    login_data = {"username": test_user.email, "password": test_password}
    response = client.post("/users/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_my_profile_success(client: TestClient, auth_headers):
    response = client.get("/users/me/profile", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
