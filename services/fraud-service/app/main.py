import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException

from app.consumers.transaction_consumer import (
    start_consumer
)
from app.core.config import settings
from app.db.database import (
    AsyncSessionLocal,
    Base,
    engine
)
from app.schemas.fraud_alert import (
    FraudAlertResponse,
    FraudStatsResponse
)
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse
)
from app.services.feature_store import (
    get_country,
    increment_transaction_count,
    save_country,
    save_last_transaction
)
from app.services.fraud_engine import (
    calculate_fraud_score
)
from app.services.fraud_service import (
    get_alert_by_id,
    get_alert_stats,
    get_alerts,
    save_alert
)
from app.services.ml_fraud_engine import (
    predict_fraud_probability
)
from app.services.model_loader import (
    model_loader
)
from app.services.transaction_status import (
    map_risk_level_to_transaction_status,
    update_transaction_status
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

worker_task: asyncio.Task | None = None


def get_country_features(
    country: str,
    previous_country: str | None
):
    country_risk = int(
        country in ["NG", "KP", "IR"]
    )

    country_changed = int(
        previous_country is not None
        and previous_country != country
    )

    return country_risk, country_changed


def get_risk_level(
    probability: float
):
    if probability >= 0.8:
        return "HIGH"

    if probability >= 0.5:
        return "MEDIUM"

    return "LOW"


async def fraud_worker():
    while True:
        try:
            async for transaction in start_consumer():
                await process_transaction(
                    transaction
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Fraud worker loop failed, retrying in %s seconds: %s",
                settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS,
                exc
            )
            await asyncio.sleep(
                settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS
            )


async def process_transaction(
    transaction: dict
):
    user_id = transaction["user_id"]
    amount = transaction["amount"]
    country = transaction["country"]

    await save_last_transaction(
        user_id=user_id,
        amount=amount
    )

    tx_count = await increment_transaction_count(
        user_id=user_id
    )

    previous_country = await get_country(
        user_id=user_id
    )

    await save_country(
        user_id=user_id,
        country=country
    )

    score = calculate_fraud_score(
        amount=amount,
        country=country,
        tx_count=tx_count,
        previous_country=previous_country
    )

    country_risk, country_changed = get_country_features(
        country=country,
        previous_country=previous_country
    )

    probability = predict_fraud_probability(
        amount=amount,
        tx_count=tx_count,
        country_risk=country_risk,
        country_changed=country_changed
    )

    level = get_risk_level(
        probability
    )
    transaction_status = map_risk_level_to_transaction_status(
        level
    )

    logger.info(
        "Processed transaction_id=%s user_id=%s amount=%s country=%s previous_country=%s tx_count=%s score=%.4f probability=%.4f risk_level=%s transaction_status=%s",
        transaction["transaction_id"],
        user_id,
        amount,
        country,
        previous_country,
        tx_count,
        score,
        probability,
        level,
        transaction_status
    )

    async with AsyncSessionLocal() as session:
        status_updated = await update_transaction_status(
            session=session,
            transaction_id=transaction["transaction_id"],
            status=transaction_status
        )

        if not status_updated:
            logger.warning(
                "Transaction %s was not found for status update",
                transaction["transaction_id"]
            )

        await save_alert(
            session=session,
            transaction_id=transaction["transaction_id"],
            score=score,
            probability=probability,
            level=level
        )

    return {
        "transaction_id": transaction["transaction_id"],
        "fraud_score": score,
        "fraud_probability": probability,
        "risk_level": level,
        "transaction_status": transaction_status,
        "tx_count": tx_count,
        "previous_country": previous_country
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    model_loader.load()
    worker_task = asyncio.create_task(
        fraud_worker()
    )

    logger.info("Fraud Service started")

    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task


app = FastAPI(
    title="Fraud Detection Service",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return await get_health()


@app.get("/health")
async def get_health():
    return {
        "service": "fraud-service",
        "status": "running",
        "model_source": model_loader.source
    }


@app.get(
    "/alerts",
    response_model=list[FraudAlertResponse]
)
async def read_alerts():
    async with AsyncSessionLocal() as session:
        return await get_alerts(
            session
        )


@app.get(
    "/alerts/{alert_id}",
    response_model=FraudAlertResponse
)
async def read_alert(
    alert_id: int
):
    async with AsyncSessionLocal() as session:
        alert = await get_alert_by_id(
            session,
            alert_id
        )

        if alert is None:
            raise HTTPException(
                status_code=404,
                detail="Alert not found"
            )

        return alert


@app.get(
    "/stats",
    response_model=FraudStatsResponse
)
async def read_stats():
    async with AsyncSessionLocal() as session:
        return await get_alert_stats(
            session
        )


@app.post(
    "/predict",
    response_model=PredictionResponse
)
async def predict(
    payload: PredictionRequest
):
    score = calculate_fraud_score(
        amount=payload.amount,
        country=payload.country,
        tx_count=payload.tx_count,
        previous_country=payload.previous_country
    )

    country_risk, country_changed = get_country_features(
        country=payload.country,
        previous_country=payload.previous_country
    )

    probability = predict_fraud_probability(
        amount=payload.amount,
        tx_count=payload.tx_count,
        country_risk=country_risk,
        country_changed=country_changed
    )

    return PredictionResponse(
        fraud_score=score,
        fraud_probability=probability,
        risk_level=get_risk_level(probability)
    )
