import json
import time

import joblib
from flask import Flask, jsonify, request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from train import MODEL_PATH, METADATA_PATH, train_and_save

if not MODEL_PATH.exists() or not METADATA_PATH.exists():
    train_and_save()

model = joblib.load(MODEL_PATH)
metadata = json.loads(METADATA_PATH.read_text())

app = Flask(__name__)

PREDICTION_REQUESTS = Counter(
    "model_setu_ml_prediction_requests_total",
    "Total prediction requests received",
)

PREDICTIONS = Counter(
    "model_setu_ml_predictions_total",
    "Successful predictions by class",
    ["prediction", "model_version"],
)

PREDICTION_ERRORS = Counter(
    "model_setu_ml_prediction_errors_total",
    "Invalid or failed prediction requests",
    ["reason"],
)

PREDICTION_LATENCY = Histogram(
    "model_setu_ml_prediction_duration_seconds",
    "Time taken to process prediction requests",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)


@app.before_request
def start_request_timer():
    if request.path == "/predict":
        request._prediction_start_time = time.perf_counter()
        PREDICTION_REQUESTS.inc()


@app.after_request
def record_request_metrics(response):
    if request.path == "/predict":
        start_time = getattr(request, "_prediction_start_time", None)
        if start_time is not None:
            PREDICTION_LATENCY.observe(time.perf_counter() - start_time)
    return response


@app.get("/")
def index():
    return jsonify({
        "service": "Model-Setu ML Inference API",
        "status": "running",
        "model_version": metadata["model_version"],
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
    })


@app.get("/model-info")
def model_info():
    return jsonify(metadata)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        PREDICTION_ERRORS.labels(reason="invalid_json").inc()
        return jsonify({
            "error": "Send a JSON object with a features array"
        }), 400

    features = body.get("features")

    if not isinstance(features, list) or len(features) != 4:
        PREDICTION_ERRORS.labels(reason="invalid_features").inc()
        return jsonify({
            "error": "features must contain exactly 4 numeric values"
        }), 400

    try:
        features = [float(value) for value in features]
    except (TypeError, ValueError):
        PREDICTION_ERRORS.labels(reason="non_numeric_features").inc()
        return jsonify({
            "error": "All features must be numeric"
        }), 400

    try:
        prediction_id = int(model.predict([features])[0])
        probabilities = model.predict_proba([features])[0]
    except Exception:
        PREDICTION_ERRORS.labels(reason="inference_failure").inc()
        app.logger.exception("Model inference failed")
        return jsonify({"error": "Model inference failed"}), 500

    predicted_class = metadata["classes"][prediction_id]

    PREDICTIONS.labels(
        prediction=predicted_class,
        model_version=metadata["model_version"],
    ).inc()

    return jsonify({
        "prediction": predicted_class,
        "class_id": prediction_id,
        "confidence": round(float(max(probabilities)), 4),
        "model_name": metadata["model_name"],
        "model_version": metadata["model_version"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
