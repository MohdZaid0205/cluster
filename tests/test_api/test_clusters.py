import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import uuid4

from api.models.cluster import ClusterCore

def test_create_cluster_success(client: TestClient, test_user, auth_headers):
    cluster_data = {
        "name": "API Test Cluster",
        "category": "API",
        "is_private": False,
        "description": "Created via API",
        "creator_uid": str(test_user.uid),
        "tags": "api, test"
    }

    response = client.post("/clusters/", json=cluster_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cid" in data
    assert data["name"] == "API Test Cluster"
    assert data["member_count"] == 1
    assert data["creator_uid"] == str(test_user.uid)

def test_get_cluster_success(client: TestClient, test_user, session: Session, auth_headers):
    # First create a cluster
    cluster_data = {
        "name": "Get Test Cluster",
        "category": "Test",
        "creator_uid": str(test_user.uid)
    }
    create_response = client.post("/clusters/", json=cluster_data, headers=auth_headers)
    cid = create_response.json()["cid"]

    # Now get it
    response = client.get(f"/clusters/{cid}")
    assert response.status_code == 200
    data = response.json()
    assert data["cid"] == cid
    assert data["name"] == "Get Test Cluster"
    assert data["member_count"] == 1

def test_get_cluster_not_found(client: TestClient):
    response = client.get(f"/clusters/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Cluster not found"

def test_list_clusters(client: TestClient, test_user, auth_headers):
    # Create two clusters with different categories
    client.post("/clusters/", json={"name": "C1", "category": "Cat1", "creator_uid": str(test_user.uid)}, headers=auth_headers)
    client.post("/clusters/", json={"name": "C2", "category": "Cat2", "creator_uid": str(test_user.uid)}, headers=auth_headers)
    
    # List all
    response = client.get("/clusters/")
    assert response.status_code == 200
    assert len(response.json()) >= 2
    
    # List by category
    response_cat1 = client.get("/clusters/?category=Cat1")
    assert response_cat1.status_code == 200
    assert all(c["category"] == "Cat1" for c in response_cat1.json())
