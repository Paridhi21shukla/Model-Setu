from flask import Flask, jsonify, Response, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

from backend.database import (
    init_db,
    create_deployment,
    get_all_deployments,
    get_deployment_by_id
)

app = Flask(__name__)

PROJECT_NAME = "Model-Setu"
APP_VERSION = "0.1.0"

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
def start_timer():
    from flask import g
    g.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):
    from flask import g

    endpoint = request.endpoint or "unknown"

    REQUEST_COUNT.labels(
        request.method, endpoint, str(response.status_code)
    ).inc()

    if hasattr(g, "start_time"):
        REQUEST_LATENCY.labels(endpoint).observe(
            time.perf_counter() - g.start_time
        )

    return response


@app.get("/")
def index():
    return jsonify({
        "project": PROJECT_NAME,
        "message": "Model-Setu Deployment Management API",
        "status": "running"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "deployment-management-api"
    }), 200


@app.get("/version")
def version():
    return jsonify({
        "project": PROJECT_NAME,
        "version": APP_VERSION
    }), 200


@app.post("/deployments")
def add_deployment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    deployment_version = data.get("version")
    deployment_status = data.get("status")

    if not isinstance(deployment_version, str) or not deployment_version.strip():
        return jsonify({"error": "Valid version is required"}), 400

    if deployment_status not in ("success", "failed", "pending"):
        return jsonify({
            "error": "Status must be success, failed, or pending"
        }), 400

    deployment = create_deployment(
        deployment_version,
        deployment_status
    )

    return jsonify({
        "message": "Deployment recorded successfully",
        "deployment": deployment
    }), 201


@app.get("/deployments")
def deployment_history():
    deployments = get_all_deployments()

    return jsonify({
        "count": len(deployments),
        "deployments": deployments
    }), 200


@app.get("/deployments/<int:deployment_id>")
def deployment_details(deployment_id):
    deployment = get_deployment_by_id(deployment_id)

    if deployment is None:
        return jsonify({"error": "Deployment not found"}), 404

    return jsonify({"deployment": deployment}), 200


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# Initialize the SQLite table when the backend starts.
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
