from fastapi import FastAPI
from sqlalchemy import select

from app.db.database import engine
from app.db.database import Base
from app.db.database import AsyncSessionLocal

from app.models.transaction import Transaction

from app.schemas.transaction import TransactionCreate
from app.schemas.transaction import TransactionResponse

from app.services.kafka_producer import start_producer
from app.services.kafka_producer import stop_producer
from app.services.kafka_producer import send_transaction_event

app = FastAPI(title="AI Banking Platform")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await start_producer()
    print("API Gateway started")


@app.on_event("shutdown")
async def shutdown():
    await stop_producer()


@app.get("/")
async def root():
    return {"message": "AI Banking Platform API"}


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

        await send_transaction_event({
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "amount": transaction.amount,
            "country": transaction.country,
            "device_type": transaction.device_type
        })

        return transaction


@app.get("/transactions")
async def get_transactions():

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Transaction)
        )

        transactions = result.scalars().all()

        return transactions