import importlib
import asyncio

from tests.helpers import import_service_module


def test_process_transaction_creates_high_risk_alert(
    monkeypatch
):
    fraud_module = import_service_module(
        "services/fraud-service"
    )

    saved_alerts = []
    saved_predictions = []
    updated_statuses = []
    published_alert_events = []

    async def fake_save_last_transaction(user_id, amount):
        return None

    async def fake_increment_transaction_count(user_id):
        return 12

    async def fake_get_country(user_id):
        return "US"

    async def fake_get_last_transaction(user_id):
        return 4000.0

    async def fake_get_device(user_id):
        return "web"

    async def fake_get_last_transaction_time(user_id):
        return "2026-07-08T08:00:00+00:00"

    async def fake_save_country(user_id, country):
        return None

    async def fake_save_device(user_id, device_type):
        return None

    async def fake_save_last_transaction_time(user_id, occurred_at_iso):
        return None

    def fake_evaluate_model_candidates(
        features
    ):
        row = features.iloc[0].to_dict()
        assert row["previous_amount"] == 4000.0
        assert row["amount_diff"] == 11000.0
        assert row["device_changed"] == 1.0
        return {
            "champion_probability": 0.91,
            "challenger_probability": None,
            "probability_delta": None
        }

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def commit(self):
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
        return type(
            "SavedAlert",
            (),
            {
                "id": 301,
                "transaction_id": transaction_id,
                "fraud_score": score,
                "fraud_probability": probability,
                "risk_level": level
            }
        )()

    async def fake_update_transaction_status(
        session,
        transaction_id,
        status
    ):
        updated_statuses.append({
            "transaction_id": transaction_id,
            "status": status
        })
        return True

    async def fake_save_model_prediction(
        session,
        transaction_id,
        fraud_probability,
        risk_level,
        model_name,
        model_version,
        model_role,
        is_live_decision,
        model_source,
        features
    ):
        saved_predictions.append({
            "transaction_id": transaction_id,
            "fraud_probability": fraud_probability,
            "risk_level": risk_level,
            "model_name": model_name,
            "model_version": model_version,
            "model_role": model_role,
            "is_live_decision": is_live_decision,
            "model_source": model_source,
            "features": features
        })
        return type(
            "SavedPrediction",
            (),
            {
                "id": 901
            }
        )()

    async def fake_send_fraud_alert_event(payload):
        published_alert_events.append(payload)

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
        "get_last_transaction",
        fake_get_last_transaction
    )
    monkeypatch.setattr(
        fraud_module,
        "get_country",
        fake_get_country
    )
    monkeypatch.setattr(
        fraud_module,
        "get_device",
        fake_get_device
    )
    monkeypatch.setattr(
        fraud_module,
        "get_last_transaction_time",
        fake_get_last_transaction_time
    )
    monkeypatch.setattr(
        fraud_module,
        "save_country",
        fake_save_country
    )
    monkeypatch.setattr(
        fraud_module,
        "save_device",
        fake_save_device
    )
    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction_time",
        fake_save_last_transaction_time
    )
    monkeypatch.setattr(
        fraud_module,
        "evaluate_model_candidates",
        fake_evaluate_model_candidates
    )
    monkeypatch.setattr(
        fraud_module,
        "save_alert",
        fake_save_alert
    )
    monkeypatch.setattr(
        fraud_module,
        "update_transaction_status",
        fake_update_transaction_status
    )
    monkeypatch.setattr(
        fraud_module,
        "save_model_prediction",
        fake_save_model_prediction
    )
    monkeypatch.setattr(
        fraud_module,
        "send_fraud_alert_event",
        fake_send_fraud_alert_event
    )
    monkeypatch.setattr(
        fraud_module,
        "AsyncSessionLocal",
        lambda: FakeSession()
    )
    fraud_module.model_loader._model = object()
    fraud_module.model_loader._source = "test-model-source"

    result = importlib.import_module("asyncio").run(
        fraud_module.process_transaction({
            "transaction_id": 77,
            "user_id": 42,
            "amount": 15000.0,
            "country": "NG",
            "device_type": "ios",
            "created_at": "2026-07-08T12:30:00+00:00"
        })
    )

    assert result["transaction_id"] == 77
    assert result["alert_id"] == 301
    assert result["risk_level"] == "HIGH"
    assert result["transaction_status"] == "BLOCKED"
    assert result["fraud_probability"] == 0.91
    assert result["tx_count"] == 12
    assert result["previous_country"] == "US"
    assert result["previous_amount"] == 4000.0
    assert result["previous_device_type"] == "web"
    assert result["prediction_id"] == 901
    assert updated_statuses == [{
        "transaction_id": 77,
        "status": "BLOCKED"
    }]
    assert published_alert_events == [{
        "alert_id": 301,
        "transaction_id": 77,
        "fraud_score": 1.0,
        "fraud_probability": 0.91,
        "risk_level": "HIGH",
        "transaction_status": "BLOCKED"
    }]
    assert saved_alerts == [{
        "transaction_id": 77,
        "score": 1.0,
        "probability": 0.91,
        "level": "HIGH"
    }]
    assert saved_predictions == [{
        "transaction_id": 77,
        "fraud_probability": 0.91,
        "risk_level": "HIGH",
        "model_name": "FraudDetectionModel",
        "model_version": None,
        "model_role": "CHAMPION",
        "is_live_decision": True,
        "model_source": "test-model-source",
        "features": {
            "amount": 15000.0,
            "tx_count": 12.0,
            "country_risk": 1.0,
            "country_changed": 1.0,
            "previous_amount": 4000.0,
            "amount_diff": 11000.0,
            "device_changed": 1.0,
            "hour_of_day": 12.0,
            "day_of_week": 2.0
        }
    }]


def test_fraud_worker_retries_after_consumer_failure(
    monkeypatch
):
    fraud_module = import_service_module(
        "services/fraud-service"
    )

    attempts = {"count": 0}
    processed = []

    async def fake_start_consumer():
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise RuntimeError("kafka not ready")

        yield {
            "transaction_id": 5,
            "user_id": 1,
            "amount": 100.0,
            "country": "US"
        }

    async def fake_process_transaction(transaction):
        processed.append(transaction)
        raise asyncio.CancelledError

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(
        fraud_module,
        "start_consumer",
        fake_start_consumer
    )
    monkeypatch.setattr(
        fraud_module,
        "process_transaction",
        fake_process_transaction
    )
    monkeypatch.setattr(
        fraud_module.asyncio,
        "sleep",
        fake_sleep
    )

    try:
        asyncio.run(
            fraud_module.fraud_worker()
        )
    except asyncio.CancelledError:
        pass

    assert attempts["count"] >= 2
    assert processed == [{
        "transaction_id": 5,
        "user_id": 1,
        "amount": 100.0,
        "country": "US"
    }]


def test_process_transaction_saves_shadow_challenger_prediction(
    monkeypatch
):
    fraud_module = import_service_module(
        "services/fraud-service"
    )

    saved_predictions = []

    async def noop_store(*args, **kwargs):
        return None

    async def fake_increment_transaction_count(user_id):
        return 3

    async def fake_get_country(user_id):
        return "US"

    async def fake_get_last_transaction(user_id):
        return 120.0

    async def fake_get_device(user_id):
        return "android"

    async def fake_get_last_transaction_time(user_id):
        return "2026-07-08T10:00:00+00:00"

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def commit(self):
            return None

    async def fake_save_alert(
        session,
        transaction_id,
        score,
        probability,
        level
    ):
        return type(
            "SavedAlert",
            (),
            {
                "id": 88,
                "transaction_id": transaction_id,
                "fraud_score": score,
                "fraud_probability": probability,
                "risk_level": level
            }
        )()

    async def fake_update_transaction_status(
        session,
        transaction_id,
        status
    ):
        return True

    async def fake_save_model_prediction(
        session,
        transaction_id,
        fraud_probability,
        risk_level,
        model_name,
        model_version,
        model_role,
        is_live_decision,
        model_source,
        features
    ):
        saved_predictions.append({
            "transaction_id": transaction_id,
            "fraud_probability": fraud_probability,
            "risk_level": risk_level,
            "model_name": model_name,
            "model_version": model_version,
            "model_role": model_role,
            "is_live_decision": is_live_decision,
            "model_source": model_source
        })
        return type(
            "SavedPrediction",
            (),
            {
                "id": 1000 + len(saved_predictions)
            }
        )()

    async def fake_send_fraud_alert_event(payload):
        return None

    def fake_evaluate_model_candidates(features):
        return {
            "champion_probability": 0.82,
            "challenger_probability": 0.41,
            "probability_delta": 0.41
        }

    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction",
        noop_store
    )
    monkeypatch.setattr(
        fraud_module,
        "increment_transaction_count",
        fake_increment_transaction_count
    )
    monkeypatch.setattr(
        fraud_module,
        "get_last_transaction",
        fake_get_last_transaction
    )
    monkeypatch.setattr(
        fraud_module,
        "get_country",
        fake_get_country
    )
    monkeypatch.setattr(
        fraud_module,
        "get_device",
        fake_get_device
    )
    monkeypatch.setattr(
        fraud_module,
        "get_last_transaction_time",
        fake_get_last_transaction_time
    )
    monkeypatch.setattr(
        fraud_module,
        "save_country",
        noop_store
    )
    monkeypatch.setattr(
        fraud_module,
        "save_device",
        noop_store
    )
    monkeypatch.setattr(
        fraud_module,
        "save_last_transaction_time",
        noop_store
    )
    monkeypatch.setattr(
        fraud_module,
        "evaluate_model_candidates",
        fake_evaluate_model_candidates
    )
    monkeypatch.setattr(
        fraud_module,
        "save_alert",
        fake_save_alert
    )
    monkeypatch.setattr(
        fraud_module,
        "update_transaction_status",
        fake_update_transaction_status
    )
    monkeypatch.setattr(
        fraud_module,
        "save_model_prediction",
        fake_save_model_prediction
    )
    monkeypatch.setattr(
        fraud_module,
        "send_fraud_alert_event",
        fake_send_fraud_alert_event
    )
    monkeypatch.setattr(
        fraud_module,
        "AsyncSessionLocal",
        lambda: FakeSession()
    )

    fraud_module.model_loader._model = object()
    fraud_module.model_loader._source = "champion-model-source"
    fraud_module.model_loader._version = "12"
    fraud_module.challenger_model_loader._enabled = True
    fraud_module.challenger_model_loader._model = object()
    fraud_module.challenger_model_loader._source = "challenger-model-source"
    fraud_module.challenger_model_loader._version = "13"

    result = importlib.import_module("asyncio").run(
        fraud_module.process_transaction({
            "transaction_id": 91,
            "user_id": 7,
            "amount": 6500.0,
            "country": "US",
            "device_type": "ios",
            "created_at": "2026-07-08T12:30:00+00:00"
        })
    )

    assert result["risk_level"] == "HIGH"
    assert result["challenger_risk_level"] == "LOW"
    assert result["challenger_fraud_probability"] == 0.41
    assert result["probability_delta"] == 0.41
    assert result["challenger_prediction_id"] == 1002
    assert saved_predictions == [
        {
            "transaction_id": 91,
            "fraud_probability": 0.82,
            "risk_level": "HIGH",
            "model_name": "FraudDetectionModel",
            "model_version": "12",
            "model_role": "CHAMPION",
            "is_live_decision": True,
            "model_source": "champion-model-source"
        },
        {
            "transaction_id": 91,
            "fraud_probability": 0.41,
            "risk_level": "LOW",
            "model_name": "FraudDetectionModel",
            "model_version": "13",
            "model_role": "CHALLENGER",
            "is_live_decision": False,
            "model_source": "challenger-model-source"
        }
    ]

    fraud_module.challenger_model_loader._enabled = False
    fraud_module.challenger_model_loader._model = None
    fraud_module.challenger_model_loader._source = "uninitialized"
    fraud_module.challenger_model_loader._version = None


def test_create_consumer_uses_earliest_offset_reset(
    monkeypatch
):
    consumer_module = import_service_module(
        "services/fraud-service"
    )
    transaction_consumer = importlib.import_module(
        "app.consumers.transaction_consumer"
    )

    captured = {}

    class FakeConsumer:
        def __init__(self, *topics, **kwargs):
            captured["topics"] = topics
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        transaction_consumer,
        "AIOKafkaConsumer",
        FakeConsumer
    )

    transaction_consumer.create_consumer()

    assert captured["topics"] == ("transactions",)
    assert (
        captured["kwargs"]["auto_offset_reset"]
        == consumer_module.settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET
    )
    assert captured["kwargs"]["auto_offset_reset"] == "earliest"


def test_map_risk_level_to_transaction_status_defaults_to_review():
    service_module = import_service_module(
        "services/fraud-service",
        module_name="app.services.transaction_status"
    )

    assert (
        service_module.map_risk_level_to_transaction_status("LOW")
        == "APPROVED"
    )
    assert (
        service_module.map_risk_level_to_transaction_status("MEDIUM")
        == "REVIEW"
    )
    assert (
        service_module.map_risk_level_to_transaction_status("HIGH")
        == "BLOCKED"
    )
    assert (
        service_module.map_risk_level_to_transaction_status("UNKNOWN")
        == "REVIEW"
    )


def test_build_fraud_alert_event_payload():
    events_module = import_service_module(
        "services/fraud-service",
        module_name="app.services.notification_events"
    )

    alert = type(
        "Alert",
        (),
        {
            "id": 11,
            "transaction_id": 77,
            "fraud_score": 0.8,
            "fraud_probability": 0.93,
            "risk_level": "HIGH"
        }
    )()

    assert events_module.build_fraud_alert_event(
        alert,
        "BLOCKED"
    ) == {
        "alert_id": 11,
        "transaction_id": 77,
        "fraud_score": 0.8,
        "fraud_probability": 0.93,
        "risk_level": "HIGH",
        "transaction_status": "BLOCKED"
    }
