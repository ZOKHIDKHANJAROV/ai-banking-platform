# AI Banking Platform

Microservice-based fraud detection platform for banking transactions.

## Services

- `api-gateway`: accepts transactions, persists them, and publishes Kafka events.
- `fraud-service`: consumes Kafka events, calculates rule-based risk, enriches features from Redis, runs an ML model, and stores fraud alerts.
- `mlflow`: tracks experiments and serves the model registry.
- `postgres`, `redis`, `kafka`, `zookeeper`, `qdrant`: infrastructure services used by the platform.

## Current Capabilities

- Real-time transaction ingestion via FastAPI.
- Kafka event publishing from the gateway.
- Fraud alert generation with a rule engine and ML model.
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
|   `-- fraud-service/
`-- tests/
```

## API Surface

### API Gateway

- `GET /`
- `GET /health`
- `POST /transactions`
- `GET /transactions`

### Fraud Service

- `GET /`
- `GET /health`
- `GET /alerts`
- `GET /alerts/{id}`
- `GET /stats`
- `POST /predict`

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
- MLflow: `http://localhost:5000`

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
