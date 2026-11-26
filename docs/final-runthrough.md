# Model-Setu Final Run-through

This checklist is the final demonstration sequence for the current implementation. It focuses on the implemented deployment-engineering workflow: test, package, deploy, track, predict, and monitor.

## 1. Start with the repository and CI result

- Repository: https://github.com/Paridhi21shukla/Model-Setu
- Latest verified CI run at the time this guide was written: [Run #88](https://github.com/Paridhi21shukla/Model-Setu/actions/runs/45864627666)
- Commit: `8add1dda8f75b0d8d304e9542fcd3cefd751858b`
- Result: success
- Automated tests: 80 passed
- Backend Docker image validation: passed
- ML image build and GHCR publish: passed
- Render deployment trigger and live backend/ML smoke tests: passed
- Vercel frontend routes and static assets: passed
- Signed deployment completion notification: passed

Open the run and show the green job, then expand the steps if asked how the pipeline works.

## 2. Explain the architecture

1. Developer pushes code to GitHub.
2. GitHub Actions installs dependencies and runs pytest.
3. The backend Docker image is build-validated.
4. The ML-service Docker image is built and published to GHCR.
5. The workflow triggers the configured Render deployment.
6. The live backend and ML API smoke tests run, including a real sample prediction.
7. The workflow sends a signed completion event to the Flask backend.
8. The backend stores deployment history and exposes operational APIs and Prometheus metrics.
9. Prometheus scrapes configured service metrics; Grafana visualizes the metrics available to its data source.
10. The static HTML/CSS/JavaScript dashboard reads backend deployment and rollback information.

The project is a deployment-engineering pipeline for an ML application. It does not include an AI-analysis layer.

## 3. Verify production endpoints

Run these read-only checks from the project terminal:

```bash
curl -i https://model-setu-backend.onrender.com/health
curl -i https://model-setu-backend.onrender.com/version
curl -i https://model-setu.onrender.com/health
curl -i https://model-setu.onrender.com/model-info
```

Run the sample inference request:

```bash
curl -sS -X POST https://model-setu.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[5.1,3.5,1.4,0.2]}'
```

The previously verified sample response was class `setosa`, class ID `0`, confidence `1.0`, model `iris-random-forest`, version `1.0.0`. The exact prediction response should be checked again during the live demonstration.

## 4. Verify deployment tracking (read-only)

```bash
curl -sS https://model-setu-backend.onrender.com/deployments
curl -sS https://model-setu-backend.onrender.com/active-deployment
curl -sS https://model-setu-backend.onrender.com/rollback-operations
```

Show the deployment records, active deployment, and rollback-operation history. These GET requests do not change production state.

## 5. Demonstrate the frontend

Open:

- Public static frontend: https://model-setu.vercel.app/
- Deployment dashboard: https://model-setu.vercel.app/index.html
- Prediction playground: https://model-setu.vercel.app/demo.html

The GitHub Actions frontend smoke test checks the configured frontend paths and static assets. During the demo, verify the dashboard itself can load backend-backed deployment data.

## 6. Demonstrate monitoring

For the local monitoring stack, start Docker Compose from the repository root:

```bash
docker compose up --build -d
docker compose ps
```

Then open:

- Prometheus targets: http://localhost:9090/targets
- Prometheus graph: http://localhost:9090/graph
- Grafana: http://localhost:3000

Grafana credentials are the local `admin` user and the password configured by `GRAFANA_ADMIN_PASSWORD` in the uncommitted `.env` file.

Important: a dashboard panel existing is not proof that it currently has data. Check Prometheus target health and the actual panel query results. Render hosts the backend and ML service; the local Compose stack runs Prometheus and Grafana. Grafana Cloud remote-write requires its separately configured token file.

## 7. Rollback: explain and verify safely

The backend implements:

- `POST /rollback/{deployment_id}` to request a Render rollback.
- `GET /rollback/status/{rollback_id}` to check progress.
- `GET /rollback-operations` to inspect recorded rollback operations.

Automated tests cover the rollback decision logic, Render API error handling, stored deployment-ID verification, ambiguous commit matches, and terminal failure states using mocked Render responses.

**A live production rollback has not been verified end to end. Do not click a production rollback button during the final walkthrough just to demonstrate it.** A real rollback changes the deployed service. Only perform one if a specific prior deployment has been selected, the impact is understood, and the operator explicitly approves it. Otherwise, demonstrate the API design and test evidence, and state the production-verification limitation honestly.

## 8. Final local checks and clean-up

```bash
python -m pytest -v
docker compose ps
git status
git log -1 --oneline
```

If the local monitoring stack was started only for the demonstration, stop it with:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the local persistent database, Prometheus, and Grafana volumes.

## Scope and honest claims

- CI Run #88 is evidence of the workflow result at that commit; it is not a guarantee that every later deployment remains healthy.
- A live sample prediction was verified in the CI run and separately from the project terminal; repeat it during the final demo if live status matters.
- Frontend route and asset reachability passed CI; manually verify dashboard data rendering in the browser.
- Production rollback remains unverified end to end.
- Continuous production metrics ingestion and Grafana Cloud visibility should only be claimed after checking target health and actual dashboard data.
- No AI-assisted analysis or automated anomaly-detection feature is part of this project version.
