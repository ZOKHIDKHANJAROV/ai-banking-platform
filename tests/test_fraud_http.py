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

    def fake_predict_fraud_probability(**kwargs):
        captured.update(kwargs)
        return 0.72

    monkeypatch.setattr(
        fraud_module,
        "predict_fraud_probability",
        fake_predict_fraud_probability
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
        "risk_level": "MEDIUM"
    }
    assert captured == {
        "amount": 1250.0,
        "tx_count": 9,
        "country_risk": 1,
        "country_changed": 1,
        "previous_amount": 200.0,
        "amount_diff": 1050.0,
        "device_changed": 1,
        "hour_of_day": 14,
        "day_of_week": 2
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
