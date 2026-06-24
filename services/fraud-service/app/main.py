import asyncio

from fastapi import FastAPI

from app.db.database import (
    Base,
    engine
)

# регистрация модели в SQLAlchemy metadata
from app.models.fraud_alert import FraudAlert

from app.consumers.transaction_consumer import (
    start_consumer
)

from app.db.database import (
    AsyncSessionLocal
)

from app.services.fraud_engine import (
    calculate_fraud_score
)

from app.schemas.fraud_alert import (
    FraudAlertResponse
)

from fastapi import HTTPException

from app.services.fraud_service import (
    save_alert,
    get_alerts,
    get_alert_by_id
)

from app.services.feature_store import (
    save_last_transaction,
    increment_transaction_count,
    save_country,
    get_country,
    get_last_transaction
)

from app.services.feature_store import (
    get_last_transaction
)

from app.services.ml_features import (
    build_features
)

from app.services.ml_fraud_engine import (
    predict_fraud_probability
)

from app.services.statistics_service import (
    get_stats
)

app = FastAPI(
    title="Fraud Service"
)

async def fraud_worker():

    print("Fraud worker started")

    try:

        async for transaction in start_consumer():
            
            user_id = transaction["user_id"]
            amount = transaction["amount"]
            country = transaction["country"]

            previous_amount = await get_last_transaction(
                user_id=user_id
            )
            
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
                previous_country=previous_country,
                previous_amount=previous_amount
            )
            features = build_features(
                amount=amount,
                tx_count=tx_count,
                country=country,
                previous_country=previous_country,
                previous_amount=previous_amount
            )
            probability = predict_fraud_probability(
                features
            )
            if probability >= 0.8:
                level = "HIGH"

            elif probability >= 0.5:
                level = "MEDIUM"

            else:
                level = "LOW"
            print(
                f"Rule Score: {score}"
            )

            print(
                f"ML Probability: {probability:.4f}"
            )

            print(
                f"Risk Level: {level}"
            )
            async with AsyncSessionLocal() as session:

                await save_alert(
                    session=session,
                    transaction_id=transaction["transaction_id"],
                    fraud_score=score,
                    fraud_probability=probability,
                    risk_level=level
                )
                print(f"Alert saved: tx={transaction['transaction_id']}")

            print(
                "\n"
                "====================\n"
                "NEW TRANSACTION\n"
                f"{transaction}\n"
                "====================\n"
            )

    except Exception as e:

        print(
            f"Fraud worker error: {e}"
        )


@app.on_event("startup")
async def startup():

    print("Fraud Service startup")

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )

    print("Database tables checked")

    asyncio.create_task(
        fraud_worker()
    )


@app.get("/")
async def health():

    return {
        "service": "fraud-service",
        "status": "running"
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
    
@app.get("/stats")
async def stats():

    async with AsyncSessionLocal() as session:

        return await get_stats(
            session
        )