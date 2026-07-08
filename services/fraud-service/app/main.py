import asyncio
import contextlib
from datetime import datetime
from datetime import timezone
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
from app.schemas.model_prediction import (
    ModelPredictionResponse
)
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse
)
from app.schemas.training_log import (
    TrainingLogResponse
)
from app.services.feature_store import (
    get_country,
    get_device,
    get_last_transaction,
    get_last_transaction_time,
    increment_transaction_count,
    save_country,
    save_device,
    save_last_transaction,
    save_last_transaction_time
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
from app.services.kafka_producer import (
    send_fraud_alert_event,
    start_producer,
    stop_producer
)
from app.services.metrics import alerts_published_total
from app.services.metrics import kafka_worker_retries_total
from app.services.metrics import metrics_middleware
from app.services.metrics import metrics_response
from app.services.metrics import model_prediction_probability
from app.services.metrics import transactions_processed_total
from app.services.ml_fraud_engine import (
    build_features,
    predict_fraud_probability
)
from app.services.model_loader import (
    model_loader
)
from app.services.model_prediction_service import (
    get_prediction_by_id,
    get_predictions,
    save_model_prediction
)
from app.services.notification_events import (
    build_fraud_alert_event
)
from app.services.transaction_status import (
    map_risk_level_to_transaction_status,
    update_transaction_status
)
from app.services.training_log_service import (
    get_training_log_by_id,
    get_training_logs
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

worker_task: asyncio.Task | None = None


def parse_transaction_timestamp(
    timestamp_value: str | None
) -> datetime:
    if not timestamp_value:
        return datetime.now(
            timezone.utc
        )

    normalized = timestamp_value.replace(
        "Z",
        "+00:00"
    )
    parsed = datetime.fromisoformat(
        normalized
    )

    if parsed.tzinfo is None:
        return parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


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
            kafka_worker_retries_total.inc()
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
    device_type = transaction.get(
        "device_type",
        "unknown"
    )
    transaction_time = parse_transaction_timestamp(
        transaction.get("created_at")
    )
    previous_amount = await get_last_transaction(
        user_id=user_id
    )
    previous_country = await get_country(
        user_id=user_id
    )
    previous_device_type = await get_device(
        user_id=user_id
    )
    previous_transaction_time = await get_last_transaction_time(
        user_id=user_id
    )

    tx_count = await increment_transaction_count(
        user_id=user_id
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
    device_changed = int(
        previous_device_type is not None
        and previous_device_type != device_type
    )
    baseline_amount = previous_amount or amount
    amount_diff = abs(
        amount - baseline_amount
    )
    hour_of_day = transaction_time.hour
    day_of_week = transaction_time.weekday()
    features = build_features(
        amount=amount,
        tx_count=tx_count,
        country_risk=country_risk,
        country_changed=country_changed,
        previous_amount=baseline_amount,
        amount_diff=amount_diff,
        device_changed=device_changed,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week
    )

    probability = predict_fraud_probability(
        amount=amount,
        tx_count=tx_count,
        country_risk=country_risk,
        country_changed=country_changed,
        previous_amount=baseline_amount,
        amount_diff=amount_diff,
        device_changed=device_changed,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week
    )
    await save_last_transaction(
        user_id=user_id,
        amount=amount
    )
    await save_country(
        user_id=user_id,
        country=country
    )
    await save_device(
        user_id=user_id,
        device_type=device_type
    )
    await save_last_transaction_time(
        user_id=user_id,
        occurred_at_iso=transaction_time.isoformat()
    )

    level = get_risk_level(
        probability
    )
    transaction_status = map_risk_level_to_transaction_status(
        level
    )
    model_prediction_probability.set(
        probability
    )

    logger.info(
        "Processed transaction_id=%s user_id=%s amount=%s country=%s previous_country=%s previous_device=%s tx_count=%s score=%.4f probability=%.4f risk_level=%s transaction_status=%s",
        transaction["transaction_id"],
        user_id,
        amount,
        country,
        previous_country,
        previous_device_type,
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

        alert = await save_alert(
            session=session,
            transaction_id=transaction["transaction_id"],
            score=score,
            probability=probability,
            level=level
        )
        prediction = await save_model_prediction(
            session=session,
            transaction_id=transaction["transaction_id"],
            fraud_probability=probability,
            risk_level=level,
            model_source=model_loader.source,
            features=features.iloc[0].to_dict()
        )
        await session.commit()

    await send_fraud_alert_event(
        build_fraud_alert_event(
            alert=alert,
            transaction_status=transaction_status
        )
    )
    transactions_processed_total.labels(
        level,
        transaction_status
    ).inc()
    alerts_published_total.labels(
        level
    ).inc()

    return {
        "transaction_id": transaction["transaction_id"],
        "alert_id": alert.id,
        "fraud_score": score,
        "fraud_probability": probability,
        "risk_level": level,
        "transaction_status": transaction_status,
        "tx_count": tx_count,
        "previous_country": previous_country,
        "previous_amount": previous_amount,
        "previous_device_type": previous_device_type,
        "previous_transaction_time": previous_transaction_time,
        "prediction_id": prediction.id
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    await start_producer()
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

        with contextlib.suppress(Exception):
            await stop_producer()


app = FastAPI(
    title="Fraud Detection Service",
    lifespan=lifespan
)
app.middleware("http")(metrics_middleware)


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


@app.get(
    "/predictions",
    response_model=list[ModelPredictionResponse]
)
async def read_predictions():
    async with AsyncSessionLocal() as session:
        return await get_predictions(
            session
        )


@app.get(
    "/predictions/{prediction_id}",
    response_model=ModelPredictionResponse
)
async def read_prediction(
    prediction_id: int
):
    async with AsyncSessionLocal() as session:
        prediction = await get_prediction_by_id(
            session,
            prediction_id
        )

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail="Prediction not found"
            )

        return prediction


@app.get(
    "/training-logs",
    response_model=list[TrainingLogResponse]
)
async def read_training_logs():
    async with AsyncSessionLocal() as session:
        return await get_training_logs(
            session
        )


@app.get(
    "/training-logs/{training_log_id}",
    response_model=TrainingLogResponse
)
async def read_training_log(
    training_log_id: int
):
    async with AsyncSessionLocal() as session:
        training_log = await get_training_log_by_id(
            session,
            training_log_id
        )

        if training_log is None:
            raise HTTPException(
                status_code=404,
                detail="Training log not found"
            )

        return training_log


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
    baseline_amount = payload.previous_amount or payload.amount
    amount_diff = abs(
        payload.amount - baseline_amount
    )
    device_changed = int(
        payload.previous_device_type is not None
        and payload.previous_device_type != payload.device_type
    )
    transaction_time = payload.transaction_at or datetime.now(
        timezone.utc
    )

    probability = predict_fraud_probability(
        amount=payload.amount,
        tx_count=payload.tx_count,
        country_risk=country_risk,
        country_changed=country_changed,
        previous_amount=baseline_amount,
        amount_diff=amount_diff,
        device_changed=device_changed,
        hour_of_day=transaction_time.hour,
        day_of_week=transaction_time.weekday()
    )

    return PredictionResponse(
        fraud_score=score,
        fraud_probability=probability,
        risk_level=get_risk_level(probability)
    )


@app.get("/metrics")
async def get_metrics():
    return metrics_response()
