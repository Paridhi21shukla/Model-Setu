import json
from pathlib import Path

import joblib
from flask import Flask, jsonify, request

from train import MODEL_PATH, METADATA_PATH, train_and_save

if not MODEL_PATH.exists() or not METADATA_PATH.exists():
    train_and_save()

model = joblib.load(MODEL_PATH)
metadata = json.loads(METADATA_PATH.read_text())

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify({
        "service": "Model-Setu ML Inference API",
        "status": "running",
        "model_version": metadata["model_version"]
    })


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "model_loaded": model is not None})


@app.get("/model-info")
def model_info():
    return jsonify(metadata)


@app.post("/predict")
def predict():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Send a JSON object with a features array"}), 400

    features = body.get("features")
    if not isinstance(features, list) or len(features) != 4:
        return jsonify({"error": "features must contain exactly 4 numeric values"}), 400

    try:
        features = [float(value) for value in features]
    except (TypeError, ValueError):
        return jsonify({"error": "All features must be numeric"}), 400

    prediction = int(model.predict([features])[0])
    probabilities = model.predict_proba([features])[0]

    return jsonify({
        "prediction": metadata["classes"][prediction],
        "class_id": prediction,
        "confidence": round(float(max(probabilities)), 4),
        "model_name": metadata["model_name"],
        "model_version": metadata["model_version"]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
