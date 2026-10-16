from backend.app import app


def test_home_endpoint():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["project"] == "Model-Setu"


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_version_endpoint():
    client = app.test_client()
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json["version"] == "0.1.0"
