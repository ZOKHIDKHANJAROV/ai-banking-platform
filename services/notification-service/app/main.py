import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException

from app.consumers.fraud_alert_consumer import start_consumer
from app.core.config import settings
from app.core.observability import configure_logging
from app.core.observability import event_log_context
from app.core.observability import request_context_middleware
from app.db.database import AsyncSessionLocal
from app.db.database import Base
from app.db.database import engine
from app.schemas.health import HealthResponse
from app.schemas.notification import NotificationResponse
from app.services.metrics import kafka_worker_retries_total
from app.services.metrics import metrics_middleware
from app.services.metrics import metrics_response
from app.services.notification_service import get_notification_by_id
from app.services.notification_service import get_notifications
from app.services.notification_service import save_notification


configure_logging("notification-service")
logger = logging.getLogger(__name__)

worker_task: asyncio.Task | None = None


async def process_alert_event(
    alert_event: dict
):
    with event_log_context(alert_event):
        async with AsyncSessionLocal() as session:
            notification = await save_notification(
                session=session,
                alert_event=alert_event
            )

        logger.info(
            "Notification stored for fraud alert",
            extra={
                "event": "notification.persisted",
                "alert_id": notification.alert_id,
                "transaction_id": notification.transaction_id,
                "channel": notification.channel,
                "risk_level": alert_event.get("risk_level")
            }
        )

        return notification


async def notification_worker():
    while True:
        try:
            async for alert_event in start_consumer():
                await process_alert_event(
                    alert_event
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            kafka_worker_retries_total.inc()
            logger.warning(
                "Notification worker loop failed, retrying in %s seconds: %s",
                settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS,
                exc
            )
            await asyncio.sleep(
                settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    worker_task = asyncio.create_task(
        notification_worker()
    )

    logger.info("Notification Service started")

    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task


app = FastAPI(
    title="Notification Service",
    lifespan=lifespan
)
app.middleware("http")(request_context_middleware)
app.middleware("http")(metrics_middleware)


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        service="notification-service",
        status="running"
    )


@app.get("/health", response_model=HealthResponse)
async def get_health():
    return await root()


@app.get(
    "/notifications",
    response_model=list[NotificationResponse]
)
async def read_notifications():
    async with AsyncSessionLocal() as session:
        return await get_notifications(
            session
        )


@app.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse
)
async def read_notification(
    notification_id: int
):
    async with AsyncSessionLocal() as session:
        notification = await get_notification_by_id(
            session,
            notification_id
        )

        if notification is None:
            raise HTTPException(
                status_code=404,
                detail="Notification not found"
            )

        return notification


@app.get("/metrics")
async def get_metrics():
    return metrics_response()
