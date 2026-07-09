import asyncio
import importlib

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_scoring_module(
    tmp_path
):
    database_path = tmp_path / "scoring-http.db"

    return import_service_module(
        "services/scoring-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "MLFLOW_TRACKING_URI": "http://localhost:5000"
        }
    )


def prepare_scoring_app(
    scoring_module,
    monkeypatch
):
    monkeypatch.setattr(
        scoring_module.model_loader,
        "load",
        lambda: object()
    )
    scoring_module.model_loader._model = object()
    scoring_module.model_loader._source = "test-credit-model-source"


def test_scoring_health_endpoint(
    tmp_path,
    monkeypatch
):
    scoring_module = build_scoring_module(
        tmp_path
    )
    prepare_scoring_app(
        scoring_module,
        monkeypatch
    )

    with TestClient(scoring_module.app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "req-score-1",
                "X-Correlation-ID": "corr-score-1"
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "service": "scoring-service",
        "status": "running",
        "model_source": "test-credit-model-source"
    }
    assert response.headers["X-Request-ID"] == "req-score-1"
    assert response.headers["X-Correlation-ID"] == "corr-score-1"


def test_score_endpoint_persists_credit_score(
    tmp_path,
    monkeypatch
):
    scoring_module = build_scoring_module(
        tmp_path
    )
    prepare_scoring_app(
        scoring_module,
        monkeypatch
    )

    class FakeFrame:
        class _Row:
            @staticmethod
            def to_dict():
                return {
                    "age": 34,
                    "monthly_income": 4200.0
                }

        class _IlocAccessor:
            def __getitem__(
                self,
                index
            ):
                return FakeFrame._Row()

        iloc = _IlocAccessor()

    def fake_score_credit(**kwargs):
        return (
            FakeFrame(),
            0.81,
            745.5,
            "GOOD"
        )

    monkeypatch.setattr(
        scoring_module,
        "score_credit",
        fake_score_credit
    )

    with TestClient(scoring_module.app) as client:
        response = client.post(
            "/score",
            json={
                "user_id": 44,
                "age": 34,
                "monthly_income": 4200.0,
                "existing_debt": 1200.0,
                "credit_history_months": 84,
                "delinquency_count": 0,
                "utilization_ratio": 0.31,
                "active_loans": 2
            }
        )
        listed = client.get("/scores")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 44,
        "credit_score": 745.5,
        "repayment_probability": 0.81,
        "score_band": "GOOD"
    }
    assert listed.status_code == 200
    assert listed.json()[0]["user_id"] == 44
    assert listed.json()[0]["score_band"] == "GOOD"
    assert listed.json()[0]["model_source"] == "test-credit-model-source"


def test_score_by_id_returns_saved_record(
    tmp_path,
    monkeypatch
):
    scoring_module = build_scoring_module(
        tmp_path
    )
    prepare_scoring_app(
        scoring_module,
        monkeypatch
    )
    credit_score_model_module = importlib.import_module(
        "app.models.credit_score"
    )

    async def create_tables():
        async with scoring_module.engine.begin() as conn:
            await conn.run_sync(
                scoring_module.Base.metadata.create_all
            )

    async def seed_score():
        async with scoring_module.AsyncSessionLocal() as session:
            score = credit_score_model_module.CreditScore(
                user_id=88,
                credit_score=802.0,
                repayment_probability=0.913,
                score_band="EXCELLENT",
                model_source="test-credit-model-source",
                features_json='{"monthly_income": 9000.0}'
            )
            session.add(score)
            await session.commit()
            await session.refresh(score)
            return score.id

    asyncio.run(
        create_tables()
    )
    score_id = asyncio.run(
        seed_score()
    )

    with TestClient(scoring_module.app) as client:
        fetched = client.get(
            f"/scores/{score_id}"
        )

    assert fetched.status_code == 200
    assert fetched.json()["id"] == score_id
    assert fetched.json()["user_id"] == 88
    assert fetched.json()["score_band"] == "EXCELLENT"
