import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ml-service"))

from app import app, metadata


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_model_info(client):
    response = client.get("/model-info")
    assert response.status_code == 200
    assert response.json["model_version"] == "1.0.0"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["model_loaded"] is True


def test_valid_prediction(client):
    response = client.post(
        "/predict", json={"features": [5.1, 3.5, 1.4, 0.2]}
    )
    assert response.status_code == 200
    assert response.json["prediction"] in metadata["classes"]
    assert 0 <= response.json["confidence"] <= 1


def test_invalid_feature_count(client):
    response = client.post("/predict", json={"features": [5.1, 3.5]})
    assert response.status_code == 400


def test_non_numeric_features(client):
    response = client.post(
        "/predict", json={"features": ["bad", 3.5, 1.4, 0.2]}
    )
    assert response.status_code == 400


def test_missing_json(client):
    response = client.post("/predict")
    assert response.status_code == 400
