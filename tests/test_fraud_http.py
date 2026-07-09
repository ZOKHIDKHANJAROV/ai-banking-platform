import asyncio
import importlib

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_fraud_module(
    tmp_path
):
    database_path = tmp_path / "fraud-http.db"

    return import_service_module(
        "services/fraud-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }
    )


def prepare_fraud_app(
    fraud_module,
    monkeypatch
):
    async def noop():
        return None

    async def fake_fraud_worker():
        await asyncio.sleep(0)

    monkeypatch.setattr(
        fraud_module,
        "start_producer",
        noop
    )
    monkeypatch.setattr(
        fraud_module,
        "stop_producer",
        noop
    )
    monkeypatch.setattr(
        fraud_module,
        "fraud_worker",
        fake_fraud_worker
    )
    monkeypatch.setattr(
        fraud_module.model_loader,
        "load",
        lambda: None
    )
    fraud_module.model_loader._model = object()
    fraud_module.model_loader._source = "test-model-source"


def test_predict_endpoint_uses_extended_features(
    tmp_path,
    monkeypatch
):
    fraud_module = build_fraud_module(
        tmp_path
    )
    prepare_fraud_app(
        fraud_module,
        monkeypatch
    )

    captured = {}

    def fake_evaluate_model_candidates(features):
        captured.update(
            features.iloc[0].to_dict()
        )
        return {
            "champion_probability": 0.72,
            "challenger_probability": None,
            "probability_delta": None
        }

    monkeypatch.setattr(
        fraud_module,
        "evaluate_model_candidates",
        fake_evaluate_model_candidates
    )

    with TestClient(fraud_module.app) as client:
        response = client.post(
            "/predict",
            json={
                "amount": 1250.0,
                "tx_count": 9,
                "country": "NG",
                "previous_country": "US",
                "device_type": "ios",
                "previous_device_type": "android",
                "previous_amount": 200.0,
                "transaction_at": "2026-07-08T14:45:00+00:00"
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "fraud_score": 0.5,
        "fraud_probability": 0.72,
        "risk_level": "MEDIUM",
        "decision_model_role": "CHAMPION"
    }
    assert captured == {
        "amount": 1250.0,
        "tx_count": 9.0,
        "country_risk": 1,
        "country_changed": 1,
        "previous_amount": 200.0,
        "amount_diff": 1050.0,
        "device_changed": 1,
        "hour_of_day": 14,
        "day_of_week": 2
    }


def test_fraud_health_returns_request_context_headers(
    tmp_path,
    monkeypatch
):
    fraud_module = build_fraud_module(
        tmp_path
    )
    prepare_fraud_app(
        fraud_module,
        monkeypatch
    )

    with TestClient(fraud_module.app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "req-fraud-1",
                "X-Correlation-ID": "corr-fraud-1"
            }
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-fraud-1"
    assert response.headers["X-Correlation-ID"] == "corr-fraud-1"


def test_predict_endpoint_returns_challenger_shadow_details(
    tmp_path,
    monkeypatch
):
    fraud_module = build_fraud_module(
        tmp_path
    )
    prepare_fraud_app(
        fraud_module,
        monkeypatch
    )

    def fake_evaluate_model_candidates(features):
        return {
            "champion_probability": 0.84,
            "challenger_probability": 0.48,
            "probability_delta": 0.36
        }

    monkeypatch.setattr(
        fraud_module,
        "evaluate_model_candidates",
        fake_evaluate_model_candidates
    )

    with TestClient(fraud_module.app) as client:
        response = client.post(
            "/predict",
            json={
                "amount": 5400.0,
                "tx_count": 4,
                "country": "US",
                "device_type": "ios",
                "previous_country": "US",
                "previous_amount": 1000.0,
                "previous_device_type": "ios",
                "transaction_at": "2026-07-08T09:15:00+00:00"
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "fraud_score": 0.3,
        "fraud_probability": 0.84,
        "risk_level": "HIGH",
        "decision_model_role": "CHAMPION",
        "challenger_fraud_probability": 0.48,
        "challenger_risk_level": "LOW",
        "probability_delta": 0.36
    }


def test_prediction_endpoints_return_saved_predictions(
    tmp_path,
    monkeypatch
):
    fraud_module = build_fraud_module(
        tmp_path
    )
    prepare_fraud_app(
        fraud_module,
        monkeypatch
    )
    prediction_model_module = importlib.import_module(
        "app.models.model_prediction"
    )

    async def create_tables():
        async with fraud_module.engine.begin() as conn:
            await conn.run_sync(
                fraud_module.Base.metadata.create_all
            )

    async def seed_prediction():
        async with fraud_module.AsyncSessionLocal() as session:
            prediction = prediction_model_module.ModelPrediction(
                transaction_id=81,
                fraud_probability=0.88,
                risk_level="HIGH",
                model_name="FraudDetectionModel",
                model_version="7",
                model_role="CHAMPION",
                is_live_decision=True,
                model_source="test-model-source",
                features_json='{"amount": 9000.0}'
            )
            session.add(prediction)
            await session.commit()
            await session.refresh(prediction)
            return prediction.id

    asyncio.run(
        create_tables()
    )
    prediction_id = asyncio.run(
        seed_prediction()
    )

    with TestClient(fraud_module.app) as client:
        listed = client.get("/predictions")
        fetched = client.get(
            f"/predictions/{prediction_id}"
        )

    assert listed.status_code == 200
    assert listed.json()[0]["transaction_id"] == 81
    assert listed.json()[0]["risk_level"] == "HIGH"
    assert fetched.status_code == 200
    assert fetched.json()["id"] == prediction_id
    assert fetched.json()["model_source"] == "test-model-source"


def test_training_log_endpoints_return_saved_logs(
    tmp_path,
    monkeypatch
):
    fraud_module = build_fraud_module(
        tmp_path
    )
    prepare_fraud_app(
        fraud_module,
        monkeypatch
    )
    training_log_model_module = importlib.import_module(
        "app.models.training_log"
    )

    async def create_tables():
        async with fraud_module.engine.begin() as conn:
            await conn.run_sync(
                fraud_module.Base.metadata.create_all
            )

    async def seed_training_log():
        async with fraud_module.AsyncSessionLocal() as session:
            training_log = training_log_model_module.TrainingLog(
                experiment_name="fraud-detection-registry",
                model_name="FraudDetectionModel",
                model_version=3,
                run_id="run-123",
                accuracy=0.991,
                parameters_json='{"n_estimators": 120}',
                metrics_json='{"accuracy": 0.991}',
                status="SUCCESS",
                error_message=None
            )
            session.add(training_log)
            await session.commit()
            await session.refresh(training_log)
            return training_log.id

    asyncio.run(
        create_tables()
    )
    training_log_id = asyncio.run(
        seed_training_log()
    )

    with TestClient(fraud_module.app) as client:
        listed = client.get("/training-logs")
        fetched = client.get(
            f"/training-logs/{training_log_id}"
        )

    assert listed.status_code == 200
    assert listed.json()[0]["model_name"] == "FraudDetectionModel"
    assert listed.json()[0]["status"] == "SUCCESS"
    assert fetched.status_code == 200
    assert fetched.json()["id"] == training_log_id
    assert fetched.json()["run_id"] == "run-123"
