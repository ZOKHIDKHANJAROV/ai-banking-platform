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
    tmp_path,
    monkeypatch
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

    async def fake_send(notification):
        return f"provider-{notification.channel.lower()}"

    monkeypatch.setattr(
        notification_module.dispatcher,
        "send",
        fake_send
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

    assert len(created) == 3
    assert [item.channel for item in created] == [
        "SMS",
        "TELEGRAM",
        "WEBSOCKET"
    ]
    assert all(item.alert_id == 801 for item in created)
    assert all(item.transaction_id == 501 for item in created)
    assert all(item.status == "SENT" for item in created)
    assert all(item.provider_message_id is not None for item in created)

    with TestClient(notification_module.app) as client:
        listed = client.get("/notifications")
        stats = client.get("/notifications/stats")
        fetched = client.get(
            f"/notifications/{created[0].id}"
        )

    assert listed.status_code == 200
    assert len(listed.json()) == 3
    assert listed.json()[0]["alert_id"] == 801
    assert listed.json()[0]["status"] == "SENT"
    assert stats.status_code == 200
    assert stats.json() == {
        "total_notifications": 3,
        "sent_notifications": 3,
        "failed_notifications": 0,
        "pending_notifications": 0
    }
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created[0].id


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


def test_retry_notification_endpoint_recovers_failed_delivery(
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

    attempts = {"count": 0}

    async def fake_send(notification):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise RuntimeError("sms provider down")

        return "provider-sms-retry"

    monkeypatch.setattr(
        notification_module.dispatcher,
        "send",
        fake_send
    )

    with TestClient(notification_module.app) as client:
        first_batch = client.get("/health")

    assert first_batch.status_code == 200

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
                "alert_id": 900,
                "transaction_id": 300,
                "fraud_score": 0.8,
                "fraud_probability": 0.88,
                "risk_level": "HIGH",
                "transaction_status": "BLOCKED"
            }
        )
    )

    failed_sms = next(
        item
        for item in created
        if item.channel == "SMS"
    )

    assert failed_sms.status == "FAILED"
    assert failed_sms.attempts == 1
    assert failed_sms.last_error == "sms provider down"

    with TestClient(notification_module.app) as client:
        retried = client.post(
            f"/notifications/{failed_sms.id}/retry"
        )

    assert retried.status_code == 200
    assert retried.json()["status"] == "SENT"
    assert retried.json()["attempts"] == 2
    assert retried.json()["provider_message_id"] == "provider-sms-retry"
