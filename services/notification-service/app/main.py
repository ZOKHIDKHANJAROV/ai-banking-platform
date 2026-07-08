import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException

from app.consumers.fraud_alert_consumer import start_consumer
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.database import Base
from app.db.database import engine
from app.schemas.health import HealthResponse
from app.schemas.notification import NotificationResponse
from app.services.notification_service import get_notification_by_id
from app.services.notification_service import get_notifications
from app.services.notification_service import save_notification


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

worker_task: asyncio.Task | None = None


async def process_alert_event(
    alert_event: dict
):
    async with AsyncSessionLocal() as session:
        notification = await save_notification(
            session=session,
            alert_event=alert_event
        )

    logger.info(
        "Notification stored id=%s alert_id=%s transaction_id=%s channel=%s",
        notification.id,
        notification.alert_id,
        notification.transaction_id,
        notification.channel
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
