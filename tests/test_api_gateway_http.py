import importlib
from pathlib import Path
import jwt

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_gateway_module(
    tmp_path: Path
):
    database_path = tmp_path / "api-gateway-test.db"
    jwt_secret = "test-secret-with-32-byte-min-length"

    return import_service_module(
        "services/api-gateway",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "API_KEY": "test-api-key",
            "JWT_SECRET": jwt_secret,
            "JWT_ALGORITHM": "HS256",
            "JWT_AUDIENCE": "ai-banking-platform",
            "JWT_ISSUER": "auth-service",
            "ALLOWED_ORIGINS": "http://localhost:3000",
            "RATE_LIMIT_BACKEND": "memory",
            "RATE_LIMIT_REQUESTS": "10",
            "RATE_LIMIT_WINDOW_SECONDS": "60"
        }
    )


def auth_headers():
    return {
        "X-API-Key": "test-api-key"
    }


def bearer_headers(
    subject: str = "bank-ops"
):
    token = jwt.encode(
        {
            "sub": subject,
            "aud": "ai-banking-platform",
            "iss": "auth-service"
        },
        "test-secret-with-32-byte-min-length",
        algorithm="HS256"
    )
    return {
        "Authorization": f"Bearer {token}"
    }


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


def test_api_gateway_metrics_endpoint(
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
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "api_gateway_http_requests_total" in response.text
    assert "api_gateway_transactions_created_total" in response.text


def test_request_context_headers_are_returned(
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
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "req-123",
                "X-Correlation-ID": "corr-456"
            }
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert response.headers["X-Correlation-ID"] == "corr-456"


def test_gateway_rejects_missing_api_key(
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
        response = client.get("/transactions")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing credentials"


def test_gateway_accepts_valid_bearer_token(
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
        response = client.get(
            "/transactions",
            headers=bearer_headers()
        )

    assert response.status_code == 200


def test_gateway_rejects_invalid_bearer_token(
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
        response = client.get(
            "/transactions",
            headers={
                "Authorization": "Bearer invalid-token"
            }
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bearer token"


def test_gateway_rate_limits_authenticated_requests(
    tmp_path,
    monkeypatch
):
    database_path = tmp_path / "api-gateway-rate-limit.db"
    gateway_module = import_service_module(
        "services/api-gateway",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "API_KEY": "test-api-key",
            "ALLOWED_ORIGINS": "http://localhost:3000",
            "RATE_LIMIT_BACKEND": "memory",
            "RATE_LIMIT_REQUESTS": "2",
            "RATE_LIMIT_WINDOW_SECONDS": "60"
        }
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
        first = client.get(
            "/transactions",
            headers=auth_headers()
        )
        second = client.get(
            "/transactions",
            headers=auth_headers()
        )
        third = client.get(
            "/transactions",
            headers=auth_headers()
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"


def test_gateway_allows_cors_preflight(
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
        response = client.options(
            "/transactions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

    assert response.status_code in [200, 204]
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )


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
            headers=auth_headers(),
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
        outbox_response = client.get(
            "/outbox",
            headers=auth_headers()
        )

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
            headers=auth_headers(),
            json={
                "user_id": 42,
                "amount": 150.25,
                "currency": "USD",
                "country": "US",
                "device_type": "ios"
            }
        )

        stored = client.get(
            "/transactions",
            headers=auth_headers()
        )
        outbox_response = client.get(
            "/outbox",
            headers=auth_headers()
        )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    assert stored.status_code == 200
    assert stored.json()[0]["status"] == "PENDING"
    assert outbox_response.status_code == 200
    assert outbox_response.json()[0]["status"] == "FAILED"
    assert outbox_response.json()[0]["attempts"] >= 1


def test_get_transaction_by_id_returns_record(
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

    async def capture_event(topic, payload):
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
    monkeypatch.setattr(
        outbox_module,
        "send_event",
        capture_event
    )

    with TestClient(gateway_module.app) as client:
        created = client.post(
            "/transactions",
            headers=auth_headers(),
            json={
                "user_id": 99,
                "amount": 700.0,
                "currency": "usd",
                "country": "uz",
                "device_type": "web"
            }
        )
        fetched = client.get(
            f"/transactions/{created.json()['id']}",
            headers=auth_headers()
        )

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created.json()["id"]
    assert fetched.json()["status"] == "QUEUED"
