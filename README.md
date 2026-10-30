# Model-Setu

**Automated Testing, Containerization, Deployment, and Monitoring of ML Applications**

## Overview

Model-Setu is a cloud-based ML application deployment project focused on simplifying the process of deploying and monitoring machine learning applications.

The current prototype serves an Iris classification model through a Flask REST API. It uses Docker for containerization, GitHub Actions for continuous integration, Render for cloud hosting, and Prometheus and Grafana for monitoring.

## End-to-End Workflow

Git Push → GitHub Actions → Automated Tests → Docker Container → Render Deployment → API Health Checks and Predictions → Metrics and Monitoring

## Current Implementation

- Flask REST API for ML inference
- Scikit-learn Random Forest classifier trained on the Iris dataset
- Dockerfile for containerizing the ML service
- Pytest-based automated tests
- GitHub Actions CI workflow
- Live cloud deployment on Render Free
- Health, model information, prediction, and metrics endpoints
- Local Prometheus and Grafana monitoring setup

## Technology Stack

- **Language:** Python
- **API:** Flask
- **Machine Learning:** Scikit-learn, Random Forest
- **Dataset:** Iris
- **Testing:** Pytest
- **Version Control:** Git and GitHub
- **Continuous Integration:** GitHub Actions
- **Containerization:** Docker
- **Cloud Hosting:** Render
- **Monitoring:** Prometheus and Grafana

## Live Deployment

Base URL: https://model-setu.onrender.com

The following endpoints have been tested on the deployed service:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Service status |
| `/health` | GET | Health check and model-loaded status |
| `/model-info` | GET | Model metadata and information |
| `/predict` | POST | Predict an Iris flower class |
| `/metrics` | GET | Expose Prometheus-format metrics |

### Example Prediction

Send a POST request to `/predict` with JSON:

```json
{
  "features": [5.1, 3.5, 1.4, 0.2]
}
```

Example response:

```json
{
  "class_id": 0,
  "confidence": 1.0,
  "model_name": "iris-random-forest",
  "model_version": "1.0.0",
  "prediction": "setosa"
}
```

The model information endpoint reports a test accuracy of 0.90 (90%). Prediction confidence is different from overall model accuracy.

### Test the Live API

```bash
curl https://model-setu.onrender.com/health

curl https://model-setu.onrender.com/model-info

curl -X POST https://model-setu.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[5.1,3.5,1.4,0.2]}'

curl https://model-setu.onrender.com/metrics
```

Note: Render Free services may sleep after inactivity, which can cause a delay on the first request.

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/Paridhi21shukla/Model-Setu.git
cd Model-Setu
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the ML service

```bash
python ml-service/app.py
```

The service uses port 5002 by default. Open `http://localhost:5002/health` to check its status.

### 5. Run automated tests

```bash
PYTHONPATH=. python -m pytest -q
```

### 6. Run the local monitoring stack

If Docker and Docker Compose are installed:

```bash
docker compose up --build
```

Refer to the Docker Compose and monitoring configuration files for the configured services and ports.

## Planned Enhancements

- Deployment management API
- Deployment history and version tracking
- Rollback to a previous deployment
- Webhook-driven deployment triggers
- Enhanced monitoring and alerting
- AI-assisted log and anomaly analysis
- React-based deployment dashboard
- Optional AWS integration using services such as Amazon ECR, EC2, and CloudWatch

These are future enhancements and should not be considered fully implemented until developed and verified.

## Project Status

- ML inference API: implemented and tested
- Docker containerization: implemented
- Automated CI testing: configured
- Render deployment: live and API endpoints verified
- Local monitoring setup: configured and previously tested
- Deployment history, rollback, AI analysis, and React dashboard: planned

## Security

- Never commit passwords, cloud credentials, API tokens, or real environment files.
- Keep secrets in appropriate environment variables or a secret manager.
- Review changes before committing them to Git.
