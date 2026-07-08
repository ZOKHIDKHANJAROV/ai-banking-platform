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

    published_events = []

    async def noop():
        return None

    async def capture_event(payload):
        published_events.append(payload)

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
        gateway_module,
        "send_transaction_event",
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
    assert published_events[0]["transaction_id"] == body["id"]


def test_create_transaction_returns_503_when_event_publish_fails(
    tmp_path,
    monkeypatch
):
    gateway_module = build_gateway_module(
        tmp_path
    )

    async def noop():
        return None

    async def fail_event(payload):
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
        gateway_module,
        "send_transaction_event",
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

    assert response.status_code == 503
    assert response.json()["detail"] == "Transaction stored but event publication failed"
    assert stored.status_code == 200
    assert stored.json()[0]["status"] == "EVENT_FAILED"
