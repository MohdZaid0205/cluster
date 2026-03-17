import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlmodel import Session

def test_create_comment_success(client: TestClient, test_user, test_post):
    comment_data = {
        "uid": str(test_user.uid),
        "content": "API Test Comment",
        "pid": str(test_post.pid)
    }

    response = client.post("/comments/", json=comment_data)
    assert response.status_code == 200
    data = response.json()
    assert "mid" in data
    assert data["content"] == "API Test Comment"
    assert data["pid"] == str(test_post.pid)
    assert data["parent_mid"] is None

def test_create_reply_comment(client: TestClient, test_user, test_comment):
    reply_data = {
        "uid": str(test_user.uid),
        "content": "API Test Reply",
        "parent_mid": str(test_comment.mid)
    }

    response = client.post("/comments/", json=reply_data)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "API Test Reply"
    assert data["parent_mid"] == str(test_comment.mid)

def test_create_comment_invalid(client: TestClient, test_user):
    # Missing both pid and parent_mid
    comment_data = {
        "uid": str(test_user.uid),
        "content": "Invalid Comment"
    }

    response = client.post("/comments/", json=comment_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Comment must belong to a post or another comment"

def test_get_comments_for_post(client: TestClient, test_post, test_comment):
    response = client.get(f"/comments/post/{test_post.pid}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["mid"] == str(test_comment.mid) for c in data)
