import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 2
DEFAULT_TIMEOUT_SECONDS = 240

API_GATEWAY_URL = "http://127.0.0.1:8000"
FRAUD_SERVICE_URL = "http://127.0.0.1:8001"
NOTIFICATION_SERVICE_URL = "http://127.0.0.1:8002"
AUTH_SERVICE_URL = "http://127.0.0.1:8003"
SCORING_SERVICE_URL = "http://127.0.0.1:8004"
ASSISTANT_SERVICE_URL = "http://127.0.0.1:8005"
MAILHOG_URL = "http://127.0.0.1:8025"
MLFLOW_URL = "http://127.0.0.1:5000"
PROMETHEUS_URL = "http://127.0.0.1:9090"
GRAFANA_URL = "http://127.0.0.1:3000"


def log(message: str) -> None:
    print(f"[smoke] {message}")


def http_request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    payload: dict | None = None,
) -> tuple[int, str]:
    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers=headers or {},
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        body = response.read().decode("utf-8")
        return response.status, body


def get_json(
    url: str,
    *,
    headers: dict | None = None,
) -> dict | list:
    _, body = http_request(
        "GET",
        url,
        headers=headers,
    )
    return json.loads(body)


def post_json(
    url: str,
    payload: dict,
    *,
    headers: dict | None = None,
) -> dict:
    merged_headers = {
        "Content-Type": "application/json",
    }
    merged_headers.update(headers or {})
    _, body = http_request(
        "POST",
        url,
        headers=merged_headers,
        payload=payload,
    )
    return json.loads(body)


def wait_for_json(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    predicate=None,
    headers: dict | None = None,
):
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            payload = get_json(
                url,
                headers=headers,
            )

            if predicate is None or predicate(payload):
                return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        time.sleep(POLL_INTERVAL_SECONDS)

    if last_error is not None:
        raise RuntimeError(
            f"Timed out waiting for {url}: {last_error}"
        ) from last_error

    raise RuntimeError(
        f"Timed out waiting for {url}"
    )


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def get_access_token() -> str:
    payload = post_json(
        f"{AUTH_SERVICE_URL}/token",
        {
            "username": "bank-ops",
            "password": "change-me-now",
        },
    )
    return payload["access_token"]


def poll_for_transaction_state(
    transaction_id: int,
    headers: dict,
):
    return wait_for_json(
        f"{API_GATEWAY_URL}/transactions/{transaction_id}",
        predicate=lambda payload: payload.get("status") in {
            "APPROVED",
            "REVIEW",
            "BLOCKED",
        },
        headers=headers,
    )


def poll_for_fraud_alert(
    transaction_id: int,
):
    return wait_for_json(
        f"{FRAUD_SERVICE_URL}/alerts",
        predicate=lambda payload: any(
            item["transaction_id"] == transaction_id
            for item in payload
        ),
    )


def poll_for_notification(
    transaction_id: int,
):
    return wait_for_json(
        f"{NOTIFICATION_SERVICE_URL}/notifications",
        predicate=lambda payload: any(
            item["transaction_id"] == transaction_id
            for item in payload
        ),
    )


def ensure_compose_running() -> None:
    output = run_command(
        ["docker", "compose", "ps"]
    )
    if "api_gateway" not in output:
        raise RuntimeError(
            "docker compose stack does not appear to be running"
        )


def main() -> int:
    log("checking docker compose status")
    ensure_compose_running()

    log("waiting for core health endpoints")
    wait_for_json(
        f"{API_GATEWAY_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )
    wait_for_json(
        f"{AUTH_SERVICE_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )
    wait_for_json(
        f"{FRAUD_SERVICE_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )
    wait_for_json(
        f"{NOTIFICATION_SERVICE_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )
    wait_for_json(
        f"{SCORING_SERVICE_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )
    wait_for_json(
        f"{ASSISTANT_SERVICE_URL}/health",
        predicate=lambda payload: payload.get("status") == "running",
    )

    log("checking supporting endpoints")
    http_request("GET", f"{MLFLOW_URL}/")
    http_request("GET", f"{PROMETHEUS_URL}/-/ready")
    http_request("GET", f"{GRAFANA_URL}/api/health")
    http_request("GET", f"{MAILHOG_URL}/api/v2/messages")

    log("requesting auth token")
    access_token = get_access_token()
    gateway_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Request-ID": "smoke-compose-req-1",
        "X-Correlation-ID": "smoke-compose-corr-1",
    }

    log("submitting transaction through gateway")
    transaction_payload = {
        "user_id": 99101,
        "amount": 18750.0,
        "currency": "usd",
        "country": "ng",
        "device_type": "android-smoke",
    }
    created_transaction = post_json(
        f"{API_GATEWAY_URL}/transactions",
        transaction_payload,
        headers=gateway_headers,
    )
    transaction_id = created_transaction["id"]

    log(f"waiting for transaction {transaction_id} to be scored")
    stored_transaction = poll_for_transaction_state(
        transaction_id,
        gateway_headers,
    )

    if stored_transaction["status"] not in {
        "REVIEW",
        "BLOCKED",
        "APPROVED",
    }:
        raise RuntimeError(
            f"unexpected transaction status {stored_transaction['status']}"
        )

    log("waiting for fraud alert and notification records")
    alerts = poll_for_fraud_alert(
        transaction_id
    )
    notifications = poll_for_notification(
        transaction_id
    )

    matching_alerts = [
        item
        for item in alerts
        if item["transaction_id"] == transaction_id
    ]
    if not matching_alerts:
        raise RuntimeError(
            "fraud-service did not persist an alert for the smoke transaction"
        )

    matching_notifications = [
        item
        for item in notifications
        if item["transaction_id"] == transaction_id
    ]
    if not matching_notifications:
        raise RuntimeError(
            "notification-service did not persist a notification for the smoke transaction"
        )

    log("indexing assistant knowledge and querying assistant-service")
    reindex_response = post_json(
        f"{ASSISTANT_SERVICE_URL}/knowledge/reindex",
        {
            "limit": 100
        },
    )
    if reindex_response["indexed_count"] < 1:
        raise RuntimeError(
            "assistant-service did not index any fraud history"
        )

    assistant_response = post_json(
        f"{ASSISTANT_SERVICE_URL}/assistant/query",
        {
            "question": f"What happened with transaction {transaction_id}?",
            "top_k": 3
        },
    )
    if not assistant_response.get("answer"):
        raise RuntimeError(
            "assistant-service did not return an answer"
        )
    if not assistant_response.get("sources"):
        raise RuntimeError(
            "assistant-service did not return retrieval sources"
        )

    log("checking scoring-service write path")
    score_response = post_json(
        f"{SCORING_SERVICE_URL}/score",
        {
            "user_id": 99101,
            "age": 34,
            "monthly_income": 6200.0,
            "existing_debt": 1200.0,
            "credit_history_months": 48,
            "delinquency_count": 0,
            "utilization_ratio": 0.24,
            "active_loans": 2,
        },
    )
    if "credit_score" not in score_response:
        raise RuntimeError(
            "scoring-service did not return a credit_score"
        )

    scores = get_json(
        f"{SCORING_SERVICE_URL}/scores"
    )
    if not any(
        item["user_id"] == 99101
        for item in scores
    ):
        raise RuntimeError(
            "scoring-service did not persist the smoke score"
        )

    log("compose smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        raise
