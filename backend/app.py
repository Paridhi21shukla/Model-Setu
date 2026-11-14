
from flask import Flask, jsonify, Response, request
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)
import time
import hmac
import hashlib
import os
from dotenv import load_dotenv

from backend.github_service import (
    GitHubServiceError,
    get_authenticated_user,
    get_user_repositories,
    get_repository_branches,
    trigger_github_workflow,
    get_github_workflow_runs
)

load_dotenv()

from backend.database import (
    init_db,
    create_deployment,
    get_all_deployments,
    get_deployment_by_id,
    get_active_deployment,
    rollback_deployment,
    update_deployment_status,
    create_rollback_operation,
    get_rollback_operation,
    finish_rollback_operation
)

from backend.render_service import (
    list_service_deploys,
    get_service_deploy,
    rollback_render_deploy,
    RenderAPIError
)

app = Flask(__name__)


def verify_webhook_signature(payload, signature):
    secret = os.getenv("DEPLOYMENT_WEBHOOK_SECRET")

    if not secret or not signature:
        return False

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)



PROJECT_NAME = "Model-Setu"
APP_VERSION = "0.1.0"

# Prometheus metrics
REQUEST_COUNT = Counter(
    "model_setu_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "model_setu_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint"]
)


@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    latency = time.time() - request.start_time

    REQUEST_COUNT.labels(
        request.method,
        request.endpoint or "unknown",
        str(response.status_code)
    ).inc()

    REQUEST_LATENCY.labels(
        request.endpoint or "unknown"
    ).observe(latency)

    return response


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": PROJECT_NAME,
        "version": APP_VERSION,
        "message": "Model-Setu Backend is running"
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "project": PROJECT_NAME,
        "version": APP_VERSION
    }), 200


@app.route("/deployments", methods=["POST"])
def create_new_deployment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must contain JSON"
        }), 400

    deployment_version = data.get("version")
    status = data.get("status", "pending")

    if not isinstance(deployment_version, str) or not deployment_version.strip():
        return jsonify({"error": "Version is required"}), 400

    if status not in ("success", "failed", "pending"):
        return jsonify({"error": "Invalid deployment status"}), 400

    commit_sha = data.get("commit_sha")

    if commit_sha is not None and not isinstance(commit_sha, str):
        return jsonify({"error": "commit_sha must be a string"}), 400

    deployment = create_deployment(deployment_version, status, commit_sha)

    return jsonify({
        "message": "Deployment created successfully",
        "deployment": deployment
    }), 201


@app.route("/deployments", methods=["GET"])
def get_deployments():
    deployments = get_all_deployments()

    return jsonify({
        "count": len(deployments),
        "deployments": deployments
    }), 200


@app.route("/deployments/<int:deployment_id>", methods=["GET"])
def get_deployment(deployment_id):
    deployment = get_deployment_by_id(deployment_id)

    if deployment is None:
        return jsonify({"error": "Deployment not found"}), 404

    return jsonify({"deployment": deployment}), 200


@app.route("/active-deployment", methods=["GET"])
def active_deployment():
    deployment = get_active_deployment()

    if deployment is None:
        return jsonify({"error": "No active deployment found"}), 404

    return jsonify({
        "active_deployment": deployment
    }), 200


@app.route("/deployments/<int:deployment_id>/status", methods=["PATCH"])
def update_deployment(deployment_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must contain JSON"}), 400

    status = data.get("status")

    if status not in ("success", "failed"):
        return jsonify({"error": "Status must be success or failed"}), 400

    deployment = update_deployment_status(deployment_id, status)

    if deployment is None:
        return jsonify({
            "error": "Deployment not found or cannot be updated"
        }), 404

    return jsonify({
        "message": "Deployment status updated successfully",
        "deployment": deployment
    }), 200


@app.route("/rollback/<int:deployment_id>", methods=["POST"])
def rollback(deployment_id):
    deployment = get_deployment_by_id(deployment_id)

    if deployment is None:
        return jsonify({"error": "Deployment not found"}), 404

    if deployment["status"] != "success":
        return jsonify({
            "error": "Only successful deployments can be rolled back"
        }), 400

    commit_sha = deployment.get("commit_sha")

    if not commit_sha:
        return jsonify({
            "error": "Deployment does not have a commit SHA"
        }), 400

    try:
        render_deploys = list_service_deploys()

        matching_deploys = []

        for item in render_deploys:
            render_deploy = item.get("deploy", item)
            commit = render_deploy.get("commit") or {}
            render_commit_sha = commit.get("id")

            if render_commit_sha == commit_sha:
                if render_deploy.get("status") in ("live", "deactivated"):
                    matching_deploys.append(render_deploy)

        if not matching_deploys:
            return jsonify({
                "error": "No matching successful Render deployment found"
            }), 404

        target_render_deploy = matching_deploys[0]

        if target_render_deploy.get("status") == "live":
            return jsonify({
                "message": "This deployment is already live on Render"
            }), 200

        render_response = rollback_render_deploy(
            target_render_deploy["id"]
        )

        render_response = render_response.get(
            "deploy", render_response
        )

        new_render_deploy_id = render_response.get("id")

        if not new_render_deploy_id:
            return jsonify({
                "error": "Render did not return a rollback deployment ID"
            }), 502

        rollback_id, error = create_rollback_operation(
            deployment_id,
            new_render_deploy_id
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Render rollback started",
            "rollback_id": rollback_id,
            "render_deploy_id": new_render_deploy_id,
            "status": "pending"
        }), 202

    except RenderAPIError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/rollback/status/<int:rollback_id>", methods=["GET"])
def rollback_status(rollback_id):
    operation = get_rollback_operation(rollback_id)

    if operation is None:
        return jsonify({"error": "Rollback operation not found"}), 404

    if operation["status"] != "pending":
        return jsonify({
            "rollback": operation
        }), 200

    try:
        render_deploy = get_service_deploy(
            operation["render_deploy_id"]
        )

        render_deploy = render_deploy.get(
            "deploy", render_deploy
        )

        render_status = render_deploy.get("status")

        if render_status == "live":
            updated, error = finish_rollback_operation(
                rollback_id, "success"
            )

            if error:
                return jsonify({"error": error}), 400

            return jsonify({
                "message": "Render rollback completed successfully",
                "rollback": updated
            }), 200

        failed_statuses = (
            "build_failed",
            "update_failed",
            "canceled",
            "pre_deploy_failed"
        )

        if render_status in failed_statuses:
            updated, error = finish_rollback_operation(
                rollback_id, "failed"
            )

            if error:
                return jsonify({"error": error}), 400

            return jsonify({
                "message": "Render rollback failed",
                "rollback": updated,
                "render_status": render_status
            }), 200

        return jsonify({
            "message": "Render rollback is still in progress",
            "status": "pending",
            "render_status": render_status
        }), 200

    except RenderAPIError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )



@app.route("/github/user", methods=["GET"])
def github_user():
    try:
        return jsonify({
            "connected": True,
            "user": get_authenticated_user()
        }), 200
    except GitHubServiceError as exc:
        return jsonify({
            "connected": False,
            "error": str(exc)
        }), 502


@app.route("/github/repositories", methods=["GET"])
def github_repositories():
    try:
        repositories = get_user_repositories()
        return jsonify({
            "count": len(repositories),
            "repositories": repositories
        }), 200
    except GitHubServiceError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/github/repositories/<owner>/<repo_name>/branches", methods=["GET"])
def github_branches(owner, repo_name):
    try:
        branches = get_repository_branches(owner, repo_name)
        return jsonify({
            "repository": f"{owner}/{repo_name}",
            "count": len(branches),
            "branches": branches
        }), 200
    except GitHubServiceError as exc:
        return jsonify({"error": str(exc)}), 502



@app.route("/github/workflows/dispatch", methods=["POST"])
def dispatch_github_workflow():
    data = request.get_json(silent=True) or {}
    owner = data.get("owner", "Paridhi21shukla")
    repo_name = data.get("repo", "Model-Setu")
    branch = data.get("branch", "main")

    try:
        result = trigger_github_workflow(owner, repo_name, branch)
        return jsonify(result), 200
    except GitHubServiceError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/github/workflows/runs", methods=["GET"])
def github_workflow_runs():
    owner = request.args.get("owner", "Paridhi21shukla")
    repo_name = request.args.get("repo", "Model-Setu")
    branch = request.args.get("branch")

    try:
        runs = get_github_workflow_runs(owner, repo_name, branch)
        return jsonify({
            "count": len(runs),
            "runs": runs
        }), 200
    except GitHubServiceError as exc:
        return jsonify({"error": str(exc)}), 502


# Initialize database once
init_db()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/webhook", methods=["POST"])
def deployment_webhook():
    secret = os.getenv("DEPLOYMENT_WEBHOOK_SECRET")
    if not secret:
        return jsonify({"error": "Webhook secret is not configured"}), 503

    payload = request.get_data(cache=True)
    signature = request.headers.get("X-Model-Setu-Signature", "")

    if not verify_webhook_signature(payload, signature):
        return jsonify({"error": "Invalid webhook signature"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    event = data.get("event")
    run_id = data.get("run_id")
    commit_sha = data.get("commit_sha")
    version = data.get("version")

    if not isinstance(run_id, str) or not run_id.strip():
        return jsonify({"error": "Valid run_id is required"}), 400

    if event == "start":
        if not isinstance(version, str) or not version.strip():
            return jsonify({"error": "Valid version is required"}), 400

        if not isinstance(commit_sha, str) or not commit_sha.strip():
            return jsonify({"error": "Valid commit_sha is required"}), 400

        deployment = create_deployment(
            version=version,
            status="pending",
            commit_sha=commit_sha,
            run_id=run_id
        )

        return jsonify({
            "message": "Deployment tracking started",
            "deployment_id": deployment["id"],
            "run_id": run_id,
            "status": deployment["status"]
        }), 201

    if event == "completed":
        deployment_id = data.get("deployment_id")
        status = data.get("status")

        if not isinstance(deployment_id, int) or isinstance(deployment_id, bool):
            return jsonify({"error": "Valid deployment_id is required"}), 400

        if status not in ("success", "failed"):
            return jsonify({"error": "Status must be success or failed"}), 400

        deployment = get_deployment_by_id(deployment_id)

        if deployment is None or deployment.get("run_id") != run_id:
            return jsonify({"error": "Deployment record not found for this run"}), 404

        try:
            updated = update_deployment_status(deployment_id, status)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409

        return jsonify({
            "message": "Deployment tracking completed",
            "deployment_id": updated["id"],
            "run_id": run_id,
            "status": updated["status"]
        }), 200

    return jsonify({"error": "Unsupported webhook event"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
