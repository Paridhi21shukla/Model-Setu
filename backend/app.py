from flask import Flask, jsonify

app = Flask(__name__)

PROJECT_NAME = "Model-Setu"
APP_VERSION = "0.1.0"


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
