from fastapi.testclient import TestClient
import jwt

from tests.helpers import import_service_module


def build_auth_module():
    jwt_secret = "test-secret-with-32-byte-min-length"

    return import_service_module(
        "services/auth-service",
        env_overrides={
            "AUTH_USERNAME": "bank-ops",
            "AUTH_PASSWORD": "change-me-now",
            "JWT_SECRET": jwt_secret,
            "JWT_ALGORITHM": "HS256",
            "JWT_AUDIENCE": "ai-banking-platform",
            "JWT_ISSUER": "auth-service",
            "JWT_EXPIRES_MINUTES": "60"
        }
    )


def test_auth_service_health_endpoint():
    auth_module = build_auth_module()

    with TestClient(auth_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "auth-service",
        "status": "running"
    }


def test_auth_service_issues_jwt():
    auth_module = build_auth_module()

    with TestClient(auth_module.app) as client:
        response = client.post(
            "/token",
            json={
                "username": "bank-ops",
                "password": "change-me-now"
            }
        )

    assert response.status_code == 200
    body = response.json()
    payload = jwt.decode(
        body["access_token"],
        "test-secret-with-32-byte-min-length",
        algorithms=["HS256"],
        audience="ai-banking-platform",
        issuer="auth-service"
    )

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert payload["sub"] == "bank-ops"


def test_auth_service_rejects_invalid_credentials():
    auth_module = build_auth_module()

    with TestClient(auth_module.app) as client:
        response = client.post(
            "/token",
            json={
                "username": "bank-ops",
                "password": "wrong"
            }
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
