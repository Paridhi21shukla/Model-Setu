
from flask import Flask, jsonify, Response, request
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)
import time

from backend.database import (
    init_db,
    create_deployment,
    get_all_deployments,
    get_deployment_by_id,
    get_active_deployment,
    rollback_deployment
)

app = Flask(__name__)

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

    deployment = create_deployment(deployment_version, status)

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


@app.route("/rollback/<int:deployment_id>", methods=["POST"])
def rollback(deployment_id):
    deployment, error = rollback_deployment(deployment_id)

    if error:
        status_code = 404 if error == "Deployment not found" else 400
        return jsonify({"error": error}), status_code

    return jsonify({
        "message": "Rollback successful",
        "active_deployment": deployment
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )


# Initialize database once
init_db()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
