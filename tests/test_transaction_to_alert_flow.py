import asyncio
import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_gateway_module(
    tmp_path: Path
):
    database_path = tmp_path / "gateway-flow.db"

    return import_service_module(
        "services/api-gateway",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "API_KEY": "test-api-key",
            "ALLOWED_ORIGINS": "http://localhost:3000",
            "RATE_LIMIT_BACKEND": "memory",
            "RATE_LIMIT_REQUESTS": "10",
            "RATE_LIMIT_WINDOW_SECONDS": "60",
            "OUTBOX_POLL_INTERVAL_SECONDS": "3600",
            "OUTBOX_BATCH_SIZE": "10"
        }
    )


def auth_headers():
    return {
        "X-API-Key": "test-api-key"
    }


def test_transaction_flows_from_gateway_event_to_fraud_alert(
    tmp_path,
    monkeypatch
):
    gateway_module = build_gateway_module(
        tmp_path
    )
    outbox_module = importlib.import_module(
        "app.services.outbox"
    )

    published_events = []

    async def noop():
        return None

    async def capture_event(topic, payload):
        published_events.append({
            "topic": topic,
            "payload": payload
        })

    monkeypatch.setattr(
        gateway_module,
        "start_producer",
        noop
    )
    monkeypatch.setattr(
        gateway_module,
        "stop_producer",
        noop
    )
    monkeypatch.setattr(
        outbox_module,
        "send_event",
        capture_event
    )

    with TestClient(gateway_module.app) as client:
        response = client.post(
            "/transactions",
            headers={
                **auth_headers(),
                "X-Request-ID": "req-flow-1",
                "X-Correlation-ID": "corr-flow-1"
            },
            json={
                "user_id": 501,
                "amount": 12500.0,
                "currency": "usd",
                "country": "ng",
                "device_type": "android"
            }
        )

    assert response.status_code == 200
    assert response.json()["status"] == "QUEUED"
    assert published_events
    assert published_events[0]["topic"] == "transactions"
    assert published_events[0]["payload"]["request_id"] == "req-flow-1"
    assert published_events[0]["payload"]["correlation_id"] == "corr-flow-1"

    database_path = tmp_path / "gateway-flow.db"

    fraud_module = import_service_module(
        "services/fraud-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }
    )

    async def fake_save_last_transaction(user_id, amount):
        return None

    async def fake_get_last_transaction(user_id):
        return 5100.0

    async def fake_increment_transaction_count(user_id):
        return 7

    async def fake_get_country(user_id):
        return "US"

    async def fake_get_device(user_id):
        return "web"

    async def fake_get_last_transaction_time(user_id):
        return "2026-07-08T07:00:00+00:00"

    async def fake_save_country(user_id, country):
        return None

    async def fake_save_device(user_id, device_type):
        return None

    async def fake_save_last_transaction_time(user_id, occurred_at_iso):
        return None

    def fake_evaluate_model_candidates(features):
        return {
            "champion_probability": 0.83,
            "challenger_probability": None,
            "probability_delta": None
        }

    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction",
        fake_save_last_transaction
    )
    monkeypatch.setattr(
        fraud_module,
        "get_last_transaction",
        fake_get_last_transaction
    )
    monkeypatch.setattr(
        fraud_module,
        "increment_transaction_count",
        fake_increment_transaction_count
    )
    monkeypatch.setattr(
        fraud_module,
        "get_country",
        fake_get_country
    )
    monkeypatch.setattr(
        fraud_module,
        "get_device",
        fake_get_device
    )
    monkeypatch.setattr(
        fraud_module,
        "get_last_transaction_time",
        fake_get_last_transaction_time
    )
    monkeypatch.setattr(
        fraud_module,
        "save_country",
        fake_save_country
    )
    monkeypatch.setattr(
        fraud_module,
        "save_device",
        fake_save_device
    )
    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction_time",
        fake_save_last_transaction_time
    )
    monkeypatch.setattr(
        fraud_module,
        "evaluate_model_candidates",
        fake_evaluate_model_candidates
    )
    published_alert_events = []

    async def fake_send_fraud_alert_event(payload):
        published_alert_events.append(payload)

    async def fake_save_model_prediction(
        session,
        transaction_id,
        fraud_probability,
        risk_level,
        model_name,
        model_version,
        model_role,
        is_live_decision,
        model_source,
        features
    ):
        return type(
            "SavedPrediction",
            (),
            {
                "id": 77
            }
        )()

    monkeypatch.setattr(
        fraud_module,
        "send_fraud_alert_event",
        fake_send_fraud_alert_event
    )
    monkeypatch.setattr(
        fraud_module,
        "save_model_prediction",
        fake_save_model_prediction
    )
    fraud_module.model_loader._model = object()
    fraud_module.model_loader._source = "test-model-source"

    async def create_fraud_tables():
        async with fraud_module.engine.begin() as conn:
            await conn.run_sync(
                fraud_module.Base.metadata.create_all
            )

    asyncio.run(
        create_fraud_tables()
    )

    result = asyncio.run(
        fraud_module.process_transaction(
            published_events[0]["payload"]
        )
    )

    with TestClient(gateway_module.app) as client:
        stored_transaction = client.get(
            f"/transactions/{response.json()['id']}",
            headers=auth_headers()
        )

    assert result["transaction_id"] == response.json()["id"]
    assert result["risk_level"] == "HIGH"
    assert result["transaction_status"] == "BLOCKED"
    assert result["fraud_probability"] == 0.83
    assert result["prediction_id"] == 77
    assert published_alert_events[0]["transaction_id"] == response.json()["id"]
    assert published_alert_events[0]["risk_level"] == "HIGH"
    assert published_alert_events[0]["transaction_status"] == "BLOCKED"
    assert published_alert_events[0]["request_id"] == "req-flow-1"
    assert published_alert_events[0]["correlation_id"] == "corr-flow-1"
    assert stored_transaction.status_code == 200
    assert stored_transaction.json()["status"] == "BLOCKED"
