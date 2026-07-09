# AI Banking Platform

Microservice-based fraud detection platform for banking transactions.

## Services

- `api-gateway`: accepts transactions, persists them, and publishes Kafka events.
- `fraud-service`: consumes Kafka events, calculates rule-based risk, enriches features from Redis, runs an ML model, and stores fraud alerts.
- `notification-service`: consumes fraud alerts, builds notification messages, and stores delivery records.
- `scoring-service`: generates credit scores from a registry-backed ML model and stores scoring audit records.
- `auth-service`: issues JWT access tokens for protected gateway access.
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
- API gateway hardening with API key auth, Redis-backed rate limiting, CORS, and request/correlation IDs.
- JWT token issuance via auth-service and bearer-token access to the API gateway.
- MLflow Registry-based model loading with automatic latest-version resolution.
- Optional champion-challenger shadow scoring for fraud models with audit persistence and divergence metrics.
- Fraud feature enrichment with previous amount, device change, and transaction time signals.
- Persistent `model_predictions` records with model role/version metadata for scoring auditability.
- Persistent `credit_scores` records with retrieval endpoints for credit decision auditability.
- Alert retrieval, statistics, health checks, and direct `/predict` scoring.

## Project Structure

```text
ai-banking-platform/
|-- docker-compose.yml
|-- ml/
|   `-- fraud-models/
|-- services/
|   |-- api-gateway/
|   |-- auth-service/
|   |-- fraud-service/
|   |-- scoring-service/
|   `-- notification-service/
`-- tests/
```

## API Surface

### API Gateway

- `GET /`
- `GET /health`
- `GET /metrics`
- `POST /transactions`
- `GET /transactions`
- `GET /transactions/{id}`
- `GET /outbox`

Protected gateway endpoints require the `X-API-Key` header. Public endpoints remain:
- `GET /`
- `GET /health`
- `GET /metrics`

The gateway also accepts `Authorization: Bearer <jwt>` tokens issued by the auth service.

### Auth Service

- `GET /`
- `GET /health`
- `POST /token`
- `GET /metrics`

### Fraud Service

- `GET /`
- `GET /health`
- `GET /alerts`
- `GET /alerts/{id}`
- `GET /predictions`
- `GET /predictions/{id}`
- `GET /stats`
- `POST /predict`

When `MLFLOW_ENABLE_CHALLENGER_SHADOW=true`, the fraud service evaluates a challenger model in shadow mode, stores both champion and challenger predictions, and keeps the champion as the live decision source.

### Notification Service

- `GET /`
- `GET /health`
- `GET /notifications`
- `GET /notifications/{id}`
- `GET /metrics`

### Scoring Service

- `GET /`
- `GET /health`
- `POST /score`
- `GET /scores`
- `GET /scores/{id}`
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
- Auth Service: `http://localhost:8003`
- Scoring Service: `http://localhost:8004`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

## Training the Model

Run the training script after MLflow is available:

```bash
py -3 ml/fraud-models/train.py
```

The fraud service loads the registered `FraudDetectionModel` directly from MLflow Registry. With `MLFLOW_MODEL_STAGE=latest`, it resolves the highest registered model version automatically; with an explicit stage such as `Production`, it loads that stage directly.

## Testing

```bash
py -3 -m compileall services tests
pytest
```

## CI

GitHub Actions runs on every push and pull request. The workflow installs Python dependencies, compiles the code, and runs the test suite.
