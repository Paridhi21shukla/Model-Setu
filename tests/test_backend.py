
import pytest

from backend import database
from backend.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a separate temporary database for every test.
    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        tmp_path / "test_deployments.db"
    )

    database.init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


# -------------------------
# BASIC BACKEND API TESTS
# -------------------------

def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["project"] == "Model-Setu"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_version_endpoint(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json["version"] == "0.1.0"


# -------------------------
# DEPLOYMENT CREATION TESTS
# -------------------------

def test_create_deployment(client):
    response = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success"
        }
    )

    assert response.status_code == 201
    assert response.json["deployment"]["version"] == "1.0.0"
    assert response.json["deployment"]["status"] == "success"
    assert response.json["deployment"]["is_active"] == 1


def test_create_deployment_without_json(client):
    response = client.post("/deployments")

    assert response.status_code == 400


def test_get_deployment_history(client):
    client.post(
        "/deployments",
        json={"version": "1.0.0", "status": "success"}
    )

    response = client.get("/deployments")

    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["deployments"][0]["version"] == "1.0.0"


def test_get_deployment_by_id(client):
    created = client.post(
        "/deployments",
        json={"version": "2.0.0", "status": "success"}
    )

    deployment_id = created.json["deployment"]["id"]

    response = client.get(f"/deployments/{deployment_id}")

    assert response.status_code == 200
    assert response.json["deployment"]["version"] == "2.0.0"


def test_deployment_not_found(client):
    response = client.get("/deployments/999")

    assert response.status_code == 404
    assert response.json["error"] == "Deployment not found"


def test_invalid_deployment_status(client):
    response = client.post(
        "/deployments",
        json={"version": "1.0.0", "status": "unknown"}
    )

    assert response.status_code == 400


def test_missing_deployment_version(client):
    response = client.post(
        "/deployments",
        json={"status": "success"}
    )

    assert response.status_code == 400


# -------------------------
# ACTIVE DEPLOYMENT TESTS
# -------------------------

def test_get_active_deployment(client):
    client.post(
        "/deployments",
        json={"version": "1.0.0", "status": "success"}
    )

    response = client.get("/active-deployment")

    assert response.status_code == 200
    assert response.json["active_deployment"]["version"] == "1.0.0"
    assert response.json["active_deployment"]["is_active"] == 1


def test_no_active_deployment(client):
    response = client.get("/active-deployment")

    assert response.status_code == 404
    assert response.json["error"] == "No active deployment found"


# -------------------------
# ROLLBACK TESTS
# -------------------------

def test_rollback_successful_deployment(client):
    first = client.post(
        "/deployments",
        json={"version": "1.0.0", "status": "success"}
    )

    client.post(
        "/deployments",
        json={"version": "2.0.0", "status": "success"}
    )

    first_id = first.json["deployment"]["id"]

    response = client.post(f"/rollback/{first_id}")

    assert response.status_code == 200
    assert response.json["message"] == "Rollback successful"
    assert response.json["active_deployment"]["version"] == "1.0.0"
    assert response.json["active_deployment"]["is_active"] == 1

    active_response = client.get("/active-deployment")

    assert active_response.status_code == 200
    assert active_response.json["active_deployment"]["id"] == first_id


def test_rollback_failed_deployment(client):
    failed = client.post(
        "/deployments",
        json={"version": "3.0.0", "status": "failed"}
    )

    deployment_id = failed.json["deployment"]["id"]

    response = client.post(f"/rollback/{deployment_id}")

    assert response.status_code == 400
    assert "Only successful deployments" in response.json["error"]


def test_rollback_nonexistent_deployment(client):
    response = client.post("/rollback/999")

    assert response.status_code == 404
    assert response.json["error"] == "Deployment not found"


# -------------------------
# MONITORING TESTS
# -------------------------

def test_metrics_endpoint(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.content_type


# -------------------------
# DEPLOYMENT LIFECYCLE TESTS
# -------------------------

def test_create_deployment_with_commit_sha(client):
    response = client.post(
        "/deployments",
        json={
            "version": "3.0.0",
            "status": "pending",
            "commit_sha": "abc123"
        }
    )

    assert response.status_code == 201
    deployment = response.json["deployment"]
    assert deployment["status"] == "pending"
    assert deployment["commit_sha"] == "abc123"
    assert deployment["started_at"] is not None
    assert deployment["completed_at"] is None


def test_update_deployment_status_success(client):
    created = client.post(
        "/deployments",
        json={
            "version": "3.0.0",
            "status": "pending",
            "commit_sha": "abc123"
        }
    )

    deployment_id = created.json["deployment"]["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        json={"status": "success"}
    )

    assert response.status_code == 200
    deployment = response.json["deployment"]
    assert deployment["status"] == "success"
    assert deployment["completed_at"] is not None
    assert deployment["is_active"] == 1


def test_update_deployment_status_invalid(client):
    created = client.post(
        "/deployments",
        json={"version": "3.0.0", "status": "pending"}
    )

    deployment_id = created.json["deployment"]["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        json={"status": "pending"}
    )

    assert response.status_code == 400
