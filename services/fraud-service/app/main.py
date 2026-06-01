import asyncio

from fastapi import FastAPI
from fastapi import HTTPException

from app.db.database import (
    Base,
    engine,
    AsyncSessionLocal
)

from app.services.fraud_engine import (
    calculate_fraud_score
)

from app.services.fraud_service import (
    save_alert,
    get_alerts,
    get_alert_by_id
)

from app.consumers.transaction_consumer import (
    start_consumer
)

from app.services.feature_store import (
    save_last_transaction,
    increment_transaction_count,
    save_country,
    get_country
)

from app.schemas.fraud_alert import (
    FraudAlertResponse
)

from app.services.ml_fraud_engine import (
    predict_fraud_probability
)

app = FastAPI(
    title="Fraud Detection Service"
)


async def fraud_worker():

    async for transaction in start_consumer():

        user_id = transaction["user_id"]
        amount = transaction["amount"]
        country = transaction["country"]

        # -------------------------
        # Feature Store
        # -------------------------

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

        # -------------------------
        # Rule Engine Score
        # -------------------------

        score = calculate_fraud_score(
            amount=amount,
            country=country,
            tx_count=tx_count,
            previous_country=previous_country
        )

        # -------------------------
        # ML Features
        # -------------------------

        country_risk = int(
            country in ["NG", "KP", "IR"]
        )

        country_changed = int(
            previous_country is not None
            and previous_country != country
        )

        # -------------------------
        # ML Prediction
        # -------------------------

        probability = predict_fraud_probability(
            amount=amount,
            tx_count=tx_count,
            country_risk=country_risk,
            country_changed=country_changed
        )

        # -------------------------
        # Risk Level
        # -------------------------

        if probability >= 0.8:
            level = "HIGH"

        elif probability >= 0.5:
            level = "MEDIUM"

        else:
            level = "LOW"

        # -------------------------
        # Logging
        # -------------------------

        print(
            "\n"
            "=====================================\n"
            f"Transaction ID: {transaction['transaction_id']}\n"
            f"User ID: {user_id}\n"
            f"Amount: {amount}\n"
            f"Country: {country}\n"
            f"Previous Country: {previous_country}\n"
            f"Transactions Last Hour: {tx_count}\n"
            f"Rule Score: {score}\n"
            f"ML Probability: {probability:.4f}\n"
            f"Risk Level: {level}\n"
            "=====================================\n"
        )

        # -------------------------
        # Save Alert
        # -------------------------

        async with AsyncSessionLocal() as session:

            await save_alert(
                session=session,
                transaction_id=transaction["transaction_id"],
                score=score,
                probability=probability,
                level=level
            )


@app.on_event("startup")
async def startup():

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )

    asyncio.create_task(
        fraud_worker()
    )

    print("Fraud Service started")


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

        alerts = await get_alerts(
            session
        )

        return alerts


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