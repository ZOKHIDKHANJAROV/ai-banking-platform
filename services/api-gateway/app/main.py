import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.database import Base
from app.db.database import engine
from app.models.transaction import Transaction
from app.schemas.health import HealthResponse
from app.schemas.transaction import TransactionCreate
from app.schemas.transaction import TransactionResponse
from app.services.kafka_producer import send_transaction_event
from app.services.kafka_producer import start_producer
from app.services.kafka_producer import stop_producer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await start_producer()

    try:
        yield
    finally:
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
            device_type=payload.device_type
        )

        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)

        try:
            await send_transaction_event({
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "amount": transaction.amount,
                "country": transaction.country,
                "device_type": transaction.device_type
            })
        except Exception as exc:
            logger.exception(
                "Failed to publish transaction event transaction_id=%s",
                transaction.id
            )
            transaction.status = "EVENT_FAILED"
            await session.commit()
            await session.refresh(transaction)

            raise HTTPException(
                status_code=503,
                detail="Transaction stored but event publication failed"
            ) from exc

        transaction.status = "QUEUED"
        await session.commit()
        await session.refresh(transaction)

        return transaction


@app.get("/transactions", response_model=list[TransactionResponse])
async def get_transactions():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Transaction).order_by(
                Transaction.created_at.desc()
            )
        )

        return result.scalars().all()
