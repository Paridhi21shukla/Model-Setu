
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

def test_rollback_successful_deployment(client, monkeypatch):
    from backend import app as backend_app

    first = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success",
            "commit_sha": "old-commit"
        }
    )

    client.post(
        "/deployments",
        json={
            "version": "2.0.0",
            "status": "success",
            "commit_sha": "new-commit"
        }
    )

    first_id = first.json["deployment"]["id"]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [{
            "id": "render-old-deploy",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        }]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: {"id": "render-rollback-123"}
    )

    response = client.post(f"/rollback/{first_id}")

    assert response.status_code == 202
    assert response.json["status"] == "pending"

    active_response = client.get("/active-deployment")
    assert active_response.json["active_deployment"]["version"] == "2.0.0"


def test_rollback_becomes_active_when_render_is_live(client, monkeypatch):
    from backend import app as backend_app

    first = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success",
            "commit_sha": "old-commit"
        }
    )

    client.post(
        "/deployments",
        json={
            "version": "2.0.0",
            "status": "success",
            "commit_sha": "new-commit"
        }
    )

    first_id = first.json["deployment"]["id"]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [{
            "id": "render-old-deploy",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        }]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: {"id": "render-rollback-123"}
    )

    started = client.post(f"/rollback/{first_id}")
    rollback_id = started.json["rollback_id"]

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: {"id": deploy_id, "status": "live"}
    )

    response = client.get(f"/rollback/status/{rollback_id}")

    assert response.status_code == 200
    assert response.json["rollback"]["status"] == "success"

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: pytest.fail("Completed rollback must not call Render again")
    )

    repeated = client.get(f"/rollback/status/{rollback_id}")
    assert repeated.status_code == 200
    assert repeated.json["rollback"]["status"] == "success"

    active = client.get("/active-deployment")
    assert active.json["active_deployment"]["id"] == first_id


def test_rollback_render_failure(client, monkeypatch):
    from backend import app as backend_app

    first = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success",
            "commit_sha": "old-commit"
        }
    )

    client.post(
        "/deployments",
        json={
            "version": "2.0.0",
            "status": "success",
            "commit_sha": "new-commit"
        }
    )

    first_id = first.json["deployment"]["id"]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [{
            "id": "render-old-deploy",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        }]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: {"id": "render-rollback-123"}
    )

    started = client.post(f"/rollback/{first_id}")
    rollback_id = started.json["rollback_id"]

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: {"id": deploy_id, "status": "build_failed"}
    )

    response = client.get(f"/rollback/status/{rollback_id}")

    assert response.status_code == 200
    assert response.json["rollback"]["status"] == "failed"

    active = client.get("/active-deployment")
    assert active.json["active_deployment"]["version"] == "2.0.0"


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



def test_deployment_metrics_reflect_database_records(client):
    for version, status in (
        ("test-success", "success"),
        ("test-failed", "failed"),
        ("test-pending", "pending"),
    ):
        response = client.post(
            "/deployments",
            json={"version": version, "status": status}
        )
        assert response.status_code == 201

    response = client.get("/metrics")
    metrics = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "model_setu_deployments_total 3.0" in metrics
    assert 'model_setu_deployments_by_status{status="success"} 1.0' in metrics
    assert 'model_setu_deployments_by_status{status="failed"} 1.0' in metrics
    assert 'model_setu_deployments_by_status{status="pending"} 1.0' in metrics
    assert "model_setu_active_deployment 1.0" in metrics
    assert "model_setu_latest_deployment_timestamp" in metrics


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


# -------------------------
# SECURE WEBHOOK TESTS
# -------------------------

import hashlib
import hmac
import json


def make_webhook_signature(payload, secret):
    return "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", "test-secret")

    response = client.post(
        "/webhook",
        data=b'{"event":"start"}',
        headers={"X-Model-Setu-Signature": "sha256=invalid"},
        content_type="application/json"
    )

    assert response.status_code == 401


def test_webhook_rejects_missing_secret(client, monkeypatch):
    monkeypatch.delenv("DEPLOYMENT_WEBHOOK_SECRET", raising=False)

    response = client.post("/webhook", json={"event": "start"})

    assert response.status_code == 503


def test_webhook_start_event(client, monkeypatch):
    secret = "test-secret"
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", secret)

    payload = json.dumps({
        "event": "start",
        "run_id": "test-run-456",
        "version": "ci-456",
        "commit_sha": "test-commit-456"
    }, separators=(",", ":")).encode()

    signature = make_webhook_signature(payload, secret)

    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Model-Setu-Signature": signature},
        content_type="application/json"
    )

    assert response.status_code == 201
    assert response.json["status"] == "pending"
    assert response.json["run_id"] == "test-run-456"


def test_webhook_completion_event(client, monkeypatch):
    from backend import app as backend_app

    secret = "test-secret"
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", secret)

    monkeypatch.setattr(
        backend_app,
        "find_render_deployment_by_commit",
        lambda commit_sha: {
            "id": "dep-render-test-789",
            "status": "live",
            "commit": {"id": commit_sha}
        }
    )

    deployment = database.create_deployment(
        version="ci-789",
        status="pending",
        commit_sha="test-commit-789",
        run_id="test-run-789"
    )

    payload = json.dumps({
        "event": "completed",
        "run_id": "test-run-789",
        "deployment_id": deployment["id"],
        "status": "success"
    }, separators=(",", ":")).encode()

    signature = make_webhook_signature(payload, secret)

    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Model-Setu-Signature": signature},
        content_type="application/json"
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["render_deploy_id"] == "dep-render-test-789"

    saved = database.get_deployment_by_id(deployment["id"])
    assert saved["render_deploy_id"] == "dep-render-test-789"


def test_webhook_rejects_wrong_run_id(client, monkeypatch):
    secret = "test-secret"
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", secret)

    deployment = database.create_deployment(
        version="ci-999",
        status="pending",
        run_id="correct-run-id"
    )

    payload = json.dumps({
        "event": "completed",
        "run_id": "wrong-run-id",
        "deployment_id": deployment["id"],
        "status": "success"
    }, separators=(",", ":")).encode()

    signature = make_webhook_signature(payload, secret)

    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Model-Setu-Signature": signature},
        content_type="application/json"
    )

    assert response.status_code == 404


def test_create_deployment_saves_render_deploy_id(client):
    deployment = database.create_deployment(
        version="ci-render-1",
        status="pending",
        commit_sha="commit-render-1",
        run_id="run-render-1",
        render_deploy_id="dep-render-123"
    )

    assert deployment["render_deploy_id"] == "dep-render-123"


def test_update_deployment_status_saves_render_deploy_id(client):
    deployment = database.create_deployment(
        version="ci-render-2",
        status="pending",
        run_id="run-render-2"
    )

    updated = database.update_deployment_status(
        deployment["id"],
        "success",
        render_deploy_id="dep-render-456"
    )

    assert updated["status"] == "success"
    assert updated["render_deploy_id"] == "dep-render-456"


def test_update_deployment_status_preserves_existing_render_id(client):
    deployment = database.create_deployment(
        version="ci-render-3",
        status="pending",
        run_id="run-render-3",
        render_deploy_id="dep-render-789"
    )

    updated = database.update_deployment_status(
        deployment["id"],
        "success"
    )

    assert updated["render_deploy_id"] == "dep-render-789"


def test_find_render_deployment_by_commit(monkeypatch):
    from backend import app as backend_app

    render_deployments = [
        {
            "id": "dep-old",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        },
        {
            "id": "dep-current",
            "status": "live",
            "commit": {"id": "current-commit"}
        }
    ]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: render_deployments
    )

    result = backend_app.find_render_deployment_by_commit("current-commit")

    assert result["id"] == "dep-current"
    assert result["status"] == "live"


def test_find_render_deployment_by_commit_not_found(monkeypatch):
    from backend import app as backend_app

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: []
    )

    assert backend_app.find_render_deployment_by_commit("unknown-commit") is None


def test_webhook_keeps_deployment_pending_when_render_is_not_live(client, monkeypatch):
    from backend import app as backend_app

    secret = "test-secret"
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", secret)

    monkeypatch.setattr(
        backend_app,
        "find_render_deployment_by_commit",
        lambda commit_sha: {
            "id": "dep-render-pending",
            "status": "build_in_progress",
            "commit": {"id": commit_sha}
        }
    )

    deployment = database.create_deployment(
        version="ci-pending",
        status="pending",
        commit_sha="test-commit-pending",
        run_id="test-run-pending"
    )

    payload = __import__("json").dumps({
        "event": "completed",
        "run_id": "test-run-pending",
        "deployment_id": deployment["id"],
        "status": "success"
    }, separators=(",", ":")).encode()

    signature = make_webhook_signature(payload, secret)

    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Model-Setu-Signature": signature},
        content_type="application/json"
    )

    saved = database.get_deployment_by_id(deployment["id"])

    assert response.status_code == 202
    assert response.json["status"] == "pending"
    assert saved["status"] == "pending"
    assert saved["render_deploy_id"] is None


def test_webhook_keeps_deployment_pending_when_render_api_fails(client, monkeypatch):
    from backend import app as backend_app

    secret = "test-secret"
    monkeypatch.setenv("DEPLOYMENT_WEBHOOK_SECRET", secret)

    def raise_render_error(commit_sha):
        raise backend_app.RenderAPIError("Render API unavailable")

    monkeypatch.setattr(
        backend_app,
        "find_render_deployment_by_commit",
        raise_render_error
    )

    deployment = database.create_deployment(
        version="ci-render-error",
        status="pending",
        commit_sha="test-commit-render-error",
        run_id="test-run-render-error"
    )

    payload = __import__("json").dumps({
        "event": "completed",
        "run_id": "test-run-render-error",
        "deployment_id": deployment["id"],
        "status": "success"
    }, separators=(",", ":")).encode()

    signature = make_webhook_signature(payload, secret)

    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Model-Setu-Signature": signature},
        content_type="application/json"
    )

    saved = database.get_deployment_by_id(deployment["id"])

    assert response.status_code == 502
    assert response.json["status"] == "pending"
    assert saved["status"] == "pending"
    assert saved["render_deploy_id"] is None


# -------------------------
# ROLLBACK SAFETY TESTS
# -------------------------

def test_rollback_prefers_stored_render_deploy_id(client, monkeypatch):
    from backend import app as backend_app

    deployment = database.create_deployment(
        "1.0.0",
        "success",
        commit_sha="old-commit",
        render_deploy_id="render-old-deploy"
    )

    verified_ids = []
    rollback_ids = []

    def mock_get_service_deploy(deploy_id):
        verified_ids.append(deploy_id)
        return {"id": deploy_id, "status": "deactivated"}

    def mock_rollback(deploy_id):
        rollback_ids.append(deploy_id)
        return {"id": "render-rollback-new"}

    monkeypatch.setattr(
        backend_app, "get_service_deploy", mock_get_service_deploy
    )
    monkeypatch.setattr(
        backend_app, "rollback_render_deploy", mock_rollback
    )
    monkeypatch.setattr(
        backend_app, "list_service_deploys",
        lambda: pytest.fail("Commit lookup should not be used")
    )

    response = client.post(f"/rollback/{deployment['id']}")

    assert response.status_code == 202
    assert verified_ids == ["render-old-deploy"]
    assert rollback_ids == ["render-old-deploy"]


def test_rollback_rejects_mismatched_stored_render_id(client, monkeypatch):
    from backend import app as backend_app

    deployment = database.create_deployment(
        "1.0.0",
        "success",
        commit_sha="old-commit",
        render_deploy_id="render-expected"
    )

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: {
            "id": "render-different",
            "status": "deactivated"
        }
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: pytest.fail("Rollback must not be triggered")
    )

    response = client.post(f"/rollback/{deployment['id']}")

    assert response.status_code == 502
    assert response.json["error"] == "Render deployment ID verification failed"


def test_rollback_rejects_ambiguous_commit_matches(client, monkeypatch):
    from backend import app as backend_app

    deployment = database.create_deployment(
        "1.0.0",
        "success",
        commit_sha="old-commit"
    )

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [
            {
                "id": "render-old-1",
                "status": "deactivated",
                "commit": {"id": "old-commit"}
            },
            {
                "id": "render-old-2",
                "status": "deactivated",
                "commit": {"id": "old-commit"}
            }
        ]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: pytest.fail("Ambiguous rollback must not be triggered")
    )

    response = client.post(f"/rollback/{deployment['id']}")

    assert response.status_code == 409
    assert "ambiguous" in response.json["error"].lower()


def test_rollback_status_not_found(client):
    response = client.get("/rollback/status/999999")

    assert response.status_code == 404
    assert response.json["error"] == "Rollback operation not found"


def test_rollback_status_render_api_error_keeps_pending(client, monkeypatch):
    from backend import app as backend_app

    first = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success",
            "commit_sha": "old-commit"
        }
    )

    client.post(
        "/deployments",
        json={
            "version": "2.0.0",
            "status": "success",
            "commit_sha": "new-commit"
        }
    )

    first_id = first.json["deployment"]["id"]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [{
            "id": "render-old-deploy",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        }]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: {"id": "render-rollback-123"}
    )

    started = client.post(f"/rollback/{first_id}")
    rollback_id = started.json["rollback_id"]

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: (_ for _ in ()).throw(
            backend_app.RenderAPIError("Temporary Render API failure")
        )
    )

    response = client.get(f"/rollback/status/{rollback_id}")

    assert response.status_code == 502
    assert response.json["error"] == "Temporary Render API failure"
    assert database.get_rollback_operation(rollback_id)["status"] == "pending"

    retry_response = client.get(f"/rollback/status/{rollback_id}")

    assert retry_response.status_code == 502


@pytest.mark.parametrize(
    "render_status",
    ["update_failed", "canceled", "pre_deploy_failed"]
)
def test_rollback_status_handles_render_failure_variants(
    client, monkeypatch, render_status
):
    from backend import app as backend_app

    first = client.post(
        "/deployments",
        json={
            "version": "1.0.0",
            "status": "success",
            "commit_sha": "old-commit"
        }
    )

    second = client.post(
        "/deployments",
        json={
            "version": "2.0.0",
            "status": "success",
            "commit_sha": "new-commit"
        }
    )

    first_id = first.json["deployment"]["id"]
    second_id = second.json["deployment"]["id"]

    monkeypatch.setattr(
        backend_app,
        "list_service_deploys",
        lambda: [{
            "id": "render-old-deploy",
            "status": "deactivated",
            "commit": {"id": "old-commit"}
        }]
    )

    monkeypatch.setattr(
        backend_app,
        "rollback_render_deploy",
        lambda deploy_id: {"id": "render-rollback-123"}
    )

    started = client.post(f"/rollback/{first_id}")
    assert started.status_code == 202

    rollback_id = started.json["rollback_id"]

    monkeypatch.setattr(
        backend_app,
        "get_service_deploy",
        lambda deploy_id: {
            "id": deploy_id,
            "status": render_status
        }
    )

    response = client.get(f"/rollback/status/{rollback_id}")

    assert response.status_code == 200
    assert response.json["rollback"]["status"] == "failed"
    assert response.json["render_status"] == render_status

    active = client.get("/active-deployment")
    assert active.json["active_deployment"]["id"] == second_id
