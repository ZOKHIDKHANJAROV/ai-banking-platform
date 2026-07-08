from app.models.fraud_alert import FraudAlert


def build_fraud_alert_event(
    alert: FraudAlert,
    transaction_status: str
) -> dict:
    return {
        "alert_id": alert.id,
        "transaction_id": alert.transaction_id,
        "fraud_score": alert.fraud_score,
        "fraud_probability": alert.fraud_probability,
        "risk_level": alert.risk_level,
        "transaction_status": transaction_status
    }
