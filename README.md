# AI Banking Platform

Microservice-based fraud detection platform for banking transactions.

## Services

- `api-gateway`: accepts transactions, persists them, and publishes Kafka events.
- `fraud-service`: consumes Kafka events, calculates rule-based risk, enriches features from Redis, runs an ML model, and stores fraud alerts.
- `notification-service`: consumes fraud alerts, builds notification messages, and stores delivery records.
- `mlflow`: tracks experiments and serves the model registry.
- `prometheus`, `grafana`: collect and visualize platform metrics.
- `postgres`, `redis`, `kafka`, `zookeeper`, `qdrant`: infrastructure services used by the platform.

## Current Capabilities

- Real-time transaction ingestion via FastAPI.
- Kafka event publishing from the gateway.
- Transactional outbox delivery from the gateway to Kafka with retry support.
- Fraud alert generation with a rule engine and ML model.
- Transaction lifecycle updates after fraud scoring (`APPROVED`, `REVIEW`, `BLOCKED`).
- Notification dispatch records generated from Kafka `fraud-alerts` events.
- Prometheus metrics endpoints on every core service plus a preprovisioned Grafana dashboard.
- MLflow-first model loading with a local artifact fallback.
- Alert retrieval, statistics, health checks, and direct `/predict` scoring.

## Project Structure

```text
ai-banking-platform/
|-- docker-compose.yml
|-- ml/
|   `-- fraud-models/
|-- services/
|   |-- api-gateway/
|   |-- fraud-service/
|   `-- notification-service/
`-- tests/
```

## API Surface

### API Gateway

- `GET /`
- `GET /health`
- `POST /transactions`
- `GET /transactions`
- `GET /transactions/{id}`
- `GET /outbox`

### Fraud Service

- `GET /`
- `GET /health`
- `GET /alerts`
- `GET /alerts/{id}`
- `GET /stats`
- `POST /predict`

### Notification Service

- `GET /`
- `GET /health`
- `GET /notifications`
- `GET /notifications/{id}`
- `GET /metrics`

### Monitoring

- Prometheus scrapes:
  - `api-gateway:8000/metrics`
  - `fraud-service:8000/metrics`
  - `notification-service:8000/metrics`
- Grafana provisions a `Platform Overview` dashboard automatically.

## Running Locally

1. Start Docker Desktop or another Docker engine.
2. Apply database migrations:

```bash
set DATABASE_URL=postgresql+asyncpg://admin:admin@localhost:5432/banking
py -3 -m alembic upgrade head
```

3. Build and start the stack:

```bash
docker compose up --build
```

4. Open the services:

- API Gateway: `http://localhost:8000`
- Fraud Service: `http://localhost:8001`
- Notification Service: `http://localhost:8002`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

## Training the Model

Run the training script after MLflow is available:

```bash
py -3 ml/fraud-models/train.py
```

The fraud service first tries to load the latest registered `FraudDetectionModel` from MLflow. If that is unavailable, it falls back to `services/fraud-service/models_artifacts/model.pkl`.

## Testing

```bash
py -3 -m compileall services tests
pytest
```

## CI

GitHub Actions runs on every push and pull request. The workflow installs Python dependencies, compiles the code, and runs the test suite.
