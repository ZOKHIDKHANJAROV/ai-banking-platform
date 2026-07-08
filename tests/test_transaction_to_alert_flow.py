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
            "OUTBOX_POLL_INTERVAL_SECONDS": "3600",
            "OUTBOX_BATCH_SIZE": "10"
        }
    )


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

    fraud_module = import_service_module(
        "services/fraud-service"
    )

    saved_alerts = []

    async def fake_save_last_transaction(user_id, amount):
        return None

    async def fake_increment_transaction_count(user_id):
        return 7

    async def fake_get_country(user_id):
        return "US"

    async def fake_save_country(user_id, country):
        return None

    def fake_predict_fraud_probability(
        amount,
        tx_count,
        country_risk,
        country_changed
    ):
        return 0.83

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_save_alert(
        session,
        transaction_id,
        score,
        probability,
        level
    ):
        saved_alerts.append({
            "transaction_id": transaction_id,
            "score": score,
            "probability": probability,
            "level": level
        })

    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction",
        fake_save_last_transaction
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
        "save_country",
        fake_save_country
    )
    monkeypatch.setattr(
        fraud_module,
        "predict_fraud_probability",
        fake_predict_fraud_probability
    )
    monkeypatch.setattr(
        fraud_module,
        "save_alert",
        fake_save_alert
    )
    monkeypatch.setattr(
        fraud_module,
        "AsyncSessionLocal",
        lambda: FakeSession()
    )

    result = asyncio.run(
        fraud_module.process_transaction(
            published_events[0]["payload"]
        )
    )

    assert result["transaction_id"] == response.json()["id"]
    assert result["risk_level"] == "HIGH"
    assert result["fraud_probability"] == 0.83
    assert saved_alerts == [{
        "transaction_id": response.json()["id"],
        "score": 1.0,
        "probability": 0.83,
        "level": "HIGH"
    }]
