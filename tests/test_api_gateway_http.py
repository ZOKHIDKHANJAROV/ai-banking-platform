import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_gateway_module(
    tmp_path: Path
):
    database_path = tmp_path / "api-gateway-test.db"

    return import_service_module(
        "services/api-gateway",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }
    )


def test_api_gateway_health_endpoint(
    tmp_path,
    monkeypatch
):
    gateway_module = build_gateway_module(
        tmp_path
    )

    async def noop():
        return None

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

    with TestClient(gateway_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api-gateway",
        "status": "running"
    }


def test_create_transaction_marks_record_as_queued(
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
                "user_id": 42,
                "amount": 150.25,
                "currency": "usd",
                "country": "us",
                "device_type": "ios"
            }
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "QUEUED"
    assert body["currency"] == "USD"
    assert body["country"] == "US"
    assert published_events
    assert published_events[0]["topic"] == "transactions"
    assert published_events[0]["payload"]["transaction_id"] == body["id"]

    with TestClient(gateway_module.app) as client:
        outbox_response = client.get("/outbox")

    assert outbox_response.status_code == 200
    assert outbox_response.json()[0]["status"] == "SENT"


def test_create_transaction_persists_for_retry_when_event_publish_fails(
    tmp_path,
    monkeypatch
):
    gateway_module = build_gateway_module(
        tmp_path
    )
    outbox_module = importlib.import_module(
        "app.services.outbox"
    )

    async def noop():
        return None

    async def fail_event(topic, payload):
        raise RuntimeError("broker unavailable")

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
        fail_event
    )

    with TestClient(gateway_module.app) as client:
        response = client.post(
            "/transactions",
            json={
                "user_id": 42,
                "amount": 150.25,
                "currency": "USD",
                "country": "US",
                "device_type": "ios"
            }
        )

        stored = client.get("/transactions")
        outbox_response = client.get("/outbox")

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    assert stored.status_code == 200
    assert stored.json()[0]["status"] == "PENDING"
    assert outbox_response.status_code == 200
    assert outbox_response.json()[0]["status"] == "FAILED"
    assert outbox_response.json()[0]["attempts"] >= 1
