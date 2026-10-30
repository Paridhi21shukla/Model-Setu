import pytest

from backend import database
from backend.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a temporary database so tests never modify real deployment data.
    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        tmp_path / "test_deployments.db"
    )
    database.init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


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


def test_create_deployment(client):
    response = client.post(
        "/deployments",
        json={"version": "1.0.0", "status": "success"}
    )

    assert response.status_code == 201
    assert response.json["deployment"]["version"] == "1.0.0"
    assert response.json["deployment"]["status"] == "success"


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
