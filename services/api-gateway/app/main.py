import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.database import Base
from app.db.database import engine
from app.models.outbox_event import OutboxEvent
from app.models.transaction import Transaction
from app.schemas.health import HealthResponse
from app.schemas.transaction import TransactionCreate
from app.schemas.transaction import TransactionResponse
from app.services.kafka_producer import start_producer
from app.services.kafka_producer import stop_producer
from app.services.outbox import dispatch_pending_events
from app.services.outbox import enqueue_transaction_event


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

publisher_task: asyncio.Task | None = None


async def flush_pending_events(
    batch_size: int | None = None
):
    async with AsyncSessionLocal() as session:
        return await dispatch_pending_events(
            session,
            batch_size=batch_size or settings.OUTBOX_BATCH_SIZE
        )


async def outbox_publisher_loop():
    while True:
        try:
            await flush_pending_events()
        except Exception:
            logger.exception(
                "Outbox publisher loop iteration failed"
            )

        await asyncio.sleep(
            settings.OUTBOX_POLL_INTERVAL_SECONDS
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global publisher_task

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await start_producer()
    publisher_task = asyncio.create_task(
        outbox_publisher_loop()
    )

    try:
        yield
    finally:
        if publisher_task is not None:
            publisher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await publisher_task

        with contextlib.suppress(Exception):
            await stop_producer()


app = FastAPI(
    title="AI Banking Platform",
    lifespan=lifespan
)


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        service="api-gateway",
        status="running"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return await root()


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(payload: TransactionCreate):
    async with AsyncSessionLocal() as session:
        transaction = Transaction(
            user_id=payload.user_id,
            amount=payload.amount,
            currency=payload.currency,
            country=payload.country,
            device_type=payload.device_type,
            status="PENDING"
        )

        session.add(transaction)
        await session.flush()
        await enqueue_transaction_event(
            session,
            transaction
        )
        await session.commit()

    with contextlib.suppress(Exception):
        await flush_pending_events(batch_size=1)

    async with AsyncSessionLocal() as session:
        stored_transaction = await session.get(
            Transaction,
            transaction.id
        )

        return stored_transaction


@app.get("/transactions", response_model=list[TransactionResponse])
async def get_transactions():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Transaction).order_by(
                Transaction.created_at.desc()
            )
        )

        return result.scalars().all()


@app.get("/outbox")
async def get_outbox_events():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OutboxEvent).order_by(
                OutboxEvent.created_at.desc(),
                OutboxEvent.id.desc()
            )
        )

        events = result.scalars().all()

        return [
            {
                "id": event.id,
                "transaction_id": event.transaction_id,
                "topic": event.topic,
                "status": event.status,
                "attempts": event.attempts,
                "last_error": event.last_error
            }
            for event in events
        ]
