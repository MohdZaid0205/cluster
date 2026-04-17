import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlmodel import Session
from api.models.post import PostCore, PostContent, PostStats

def test_create_post_success(client: TestClient, test_user, test_cluster, auth_headers):
    post_data = {
        "uid": str(test_user.uid),
        "cid": str(test_cluster.cid),
        "type": "TEXT",
        "content": "API Test Post Content",
        "tags": "api, test"
    }

    response = client.post("/posts/", json=post_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "pid" in data
    assert data["content"] == "API Test Post Content"
    assert data["likes"] == 0

def test_get_post_success(client: TestClient, test_post):
    response = client.get(f"/posts/{test_post.pid}")
    assert response.status_code == 200
    data = response.json()
    assert data["pid"] == str(test_post.pid)
    assert data["content"] == "Global Test Post"

def test_get_post_not_found(client: TestClient):
    response = client.get(f"/posts/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"

def test_list_posts(client: TestClient, test_post, test_cluster):
    response = client.get(f"/posts/?cid={test_cluster.cid}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(p["pid"] == str(test_post.pid) for p in data)

def test_react_to_post(client: TestClient, test_post, test_user, session: Session, auth_headers):
    reaction_data = {
        "uid": str(test_user.uid),
        "reaction_type": "LIKE"
    }
    
    response = client.post(f"/posts/{test_post.pid}/react", json=reaction_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["current_reaction"] == "LIKE"
    
    # Verify in DB
    stats = session.get(PostStats, test_post.pid)
    assert stats.likes == 1
