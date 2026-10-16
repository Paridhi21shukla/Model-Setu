from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

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
    from flask import request, g
    g.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):
    from flask import request, g
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


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
