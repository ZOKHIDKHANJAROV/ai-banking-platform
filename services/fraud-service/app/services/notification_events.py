from app.models.fraud_alert import FraudAlert


def build_fraud_alert_event(
    alert: FraudAlert,
    transaction_status: str,
    request_id: str | None = None,
    correlation_id: str | None = None
) -> dict:
    payload = {
        "alert_id": alert.id,
        "transaction_id": alert.transaction_id,
        "fraud_score": alert.fraud_score,
        "fraud_probability": alert.fraud_probability,
        "risk_level": alert.risk_level,
        "transaction_status": transaction_status
    }

    if request_id is not None:
        payload["request_id"] = request_id

    if correlation_id is not None:
        payload["correlation_id"] = correlation_id

    return payload
