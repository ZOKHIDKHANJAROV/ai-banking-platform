import importlib

from tests.helpers import import_service_module


def test_process_transaction_creates_high_risk_alert(
    monkeypatch
):
    fraud_module = import_service_module(
        "services/fraud-service"
    )

    saved_alerts = []

    async def fake_save_last_transaction(user_id, amount):
        return None

    async def fake_increment_transaction_count(user_id):
        return 12

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
        return 0.91

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

    result = importlib.import_module("asyncio").run(
        fraud_module.process_transaction({
            "transaction_id": 77,
            "user_id": 42,
            "amount": 15000.0,
            "country": "NG"
        })
    )

    assert result["transaction_id"] == 77
    assert result["risk_level"] == "HIGH"
    assert result["fraud_probability"] == 0.91
    assert result["tx_count"] == 12
    assert result["previous_country"] == "US"
    assert saved_alerts == [{
        "transaction_id": 77,
        "score": 1.0,
        "probability": 0.91,
        "level": "HIGH"
    }]
