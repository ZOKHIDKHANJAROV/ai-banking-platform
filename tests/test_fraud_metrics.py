import asyncio

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def test_fraud_metrics_endpoint(
    tmp_path,
    monkeypatch
):
    database_path = tmp_path / "fraud-metrics.db"
    fraud_module = import_service_module(
        "services/fraud-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }
    )

    async def noop():
        return None

    async def fake_fraud_worker():
        await asyncio.sleep(0)

    monkeypatch.setattr(
        fraud_module,
        "start_producer",
        noop
    )
    monkeypatch.setattr(
        fraud_module,
        "stop_producer",
        noop
    )
    monkeypatch.setattr(
        fraud_module,
        "fraud_worker",
        fake_fraud_worker
    )
    monkeypatch.setattr(
        fraud_module.model_loader,
        "load",
        lambda: None
    )

    with TestClient(fraud_module.app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "fraud_service_http_requests_total" in response.text
    assert "fraud_service_transactions_processed_total" in response.text
