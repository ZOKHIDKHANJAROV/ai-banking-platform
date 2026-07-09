import asyncio
import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_notification_module(
    tmp_path: Path
):
    database_path = tmp_path / "notification-test.db"

    return import_service_module(
        "services/notification-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092"
        }
    )


def test_notification_health_endpoint(
    tmp_path,
    monkeypatch
):
    notification_module = build_notification_module(
        tmp_path
    )

    async def fake_notification_worker():
        await asyncio.sleep(0)

    monkeypatch.setattr(
        notification_module,
        "notification_worker",
        fake_notification_worker
    )

    with TestClient(notification_module.app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "req-notification-1",
                "X-Correlation-ID": "corr-notification-1"
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "service": "notification-service",
        "status": "running"
    }
    assert response.headers["X-Request-ID"] == "req-notification-1"
    assert response.headers["X-Correlation-ID"] == "corr-notification-1"


def test_notification_metrics_endpoint(
    tmp_path,
    monkeypatch
):
    notification_module = build_notification_module(
        tmp_path
    )

    async def fake_notification_worker():
        await asyncio.sleep(0)

    monkeypatch.setattr(
        notification_module,
        "notification_worker",
        fake_notification_worker
    )

    with TestClient(notification_module.app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "notification_service_http_requests_total" in response.text
    assert "notification_service_notifications_created_total" in response.text


def test_process_alert_event_persists_notification(
    tmp_path
):
    notification_module = build_notification_module(
        tmp_path
    )

    async def create_tables():
        async with notification_module.engine.begin() as conn:
            await conn.run_sync(
                notification_module.Base.metadata.create_all
            )

    asyncio.run(
        create_tables()
    )

    created = asyncio.run(
        notification_module.process_alert_event(
            {
                "alert_id": 801,
                "transaction_id": 501,
                "fraud_score": 0.9,
                "fraud_probability": 0.97,
                "risk_level": "HIGH",
                "transaction_status": "BLOCKED"
            }
        )
    )

    assert created.alert_id == 801
    assert created.transaction_id == 501
    assert created.channel == "SMS"
    assert created.status == "SENT"

    with TestClient(notification_module.app) as client:
        listed = client.get("/notifications")
        fetched = client.get(
            f"/notifications/{created.id}"
        )

    assert listed.status_code == 200
    assert listed.json()[0]["alert_id"] == 801
    assert listed.json()[0]["channel"] == "SMS"
    assert "BLOCKED" in listed.json()[0]["message"]
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created.id


def test_notification_worker_retries_after_consumer_failure(
    tmp_path,
    monkeypatch
):
    notification_module = build_notification_module(
        tmp_path
    )

    attempts = {"count": 0}
    processed = []

    async def fake_start_consumer():
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise RuntimeError("kafka not ready")

        yield {
            "alert_id": 1,
            "transaction_id": 2,
            "risk_level": "HIGH",
            "transaction_status": "BLOCKED"
        }

    async def fake_process_alert_event(alert_event):
        processed.append(alert_event)
        raise asyncio.CancelledError

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(
        notification_module,
        "start_consumer",
        fake_start_consumer
    )
    monkeypatch.setattr(
        notification_module,
        "process_alert_event",
        fake_process_alert_event
    )
    monkeypatch.setattr(
        notification_module.asyncio,
        "sleep",
        fake_sleep
    )

    try:
        asyncio.run(
            notification_module.notification_worker()
        )
    except asyncio.CancelledError:
        pass

    assert attempts["count"] >= 2
    assert processed == [{
        "alert_id": 1,
        "transaction_id": 2,
        "risk_level": "HIGH",
        "transaction_status": "BLOCKED"
    }]


def test_notification_consumer_uses_earliest_offset_reset(
    tmp_path,
    monkeypatch
):
    build_notification_module(
        tmp_path
    )
    consumer_module = importlib.import_module(
        "app.consumers.fraud_alert_consumer"
    )

    captured = {}

    class FakeConsumer:
        def __init__(self, *topics, **kwargs):
            captured["topics"] = topics
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        consumer_module,
        "AIOKafkaConsumer",
        FakeConsumer
    )

    consumer_module.create_consumer()

    assert captured["topics"] == ("fraud-alerts",)
    assert captured["kwargs"]["group_id"] == "notification-dispatcher"
    assert captured["kwargs"]["auto_offset_reset"] == "earliest"
