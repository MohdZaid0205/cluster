import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlmodel import Session
from api.models.user import UserAuth, UserProfile, UserRole
from api.security import get_password_hash
from api.auth import create_access_token

def test_create_comment_success(client: TestClient, test_user, test_post, auth_headers):
    comment_data = {
        "uid": str(test_user.uid),
        "content": "API Test Comment",
        "pid": str(test_post.pid)
    }

    response = client.post("/comments/", json=comment_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "mid" in data
    assert data["content"] == "API Test Comment"
    assert data["pid"] == str(test_post.pid)
    assert data["parent_mid"] is None

def test_create_reply_comment(client: TestClient, test_user, test_comment, auth_headers):
    reply_data = {
        "uid": str(test_user.uid),
        "content": "API Test Reply",
        "parent_mid": str(test_comment.mid)
    }

    response = client.post("/comments/", json=reply_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "API Test Reply"
    assert data["parent_mid"] == str(test_comment.mid)

def test_create_comment_invalid(client: TestClient, test_user, auth_headers):
    # Missing both pid and parent_mid
    comment_data = {
        "uid": str(test_user.uid),
        "content": "Invalid Comment"
    }

    response = client.post("/comments/", json=comment_data, headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Comment must belong to a post or another comment"

def test_get_comments_for_post(client: TestClient, test_post, test_comment):
    response = client.get(f"/comments/post/{test_post.pid}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["mid"] == str(test_comment.mid) for c in data)

def test_create_comment_uses_authenticated_user_not_payload_uid(client: TestClient, session: Session, test_user, test_post):
    second_uid = uuid4()
    second_user = UserAuth(
        uid=second_uid,
        email="commenter2@example.com",
        password_hash=get_password_hash("pw"),
        role=UserRole.MEMBER,
        is_verified=True,
    )
    second_profile = UserProfile(uid=second_uid, name="Second Commenter")
    session.add(second_user)
    session.add(second_profile)
    session.commit()

    second_token = create_access_token(data={"sub": str(second_uid)})
    second_headers = {"Authorization": f"Bearer {second_token}"}

    spoofed_payload = {
        "uid": str(test_user.uid),
        "content": "I am commenting as the authenticated second user",
        "pid": str(test_post.pid),
    }

    response = client.post("/comments/", json=spoofed_payload, headers=second_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == str(second_uid)

def test_create_comment_reply_with_invalid_parent_returns_400(client: TestClient, test_user, test_post, auth_headers):
    reply_data = {
        "uid": str(test_user.uid),
        "content": "Reply should fail",
        "pid": str(test_post.pid),
        "parent_mid": str(uuid4()),
    }

    response = client.post("/comments/", json=reply_data, headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Parent comment not found"
