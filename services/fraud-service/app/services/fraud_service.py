from sqlalchemy import func
from sqlalchemy import select

from app.models.fraud_alert import FraudAlert


async def save_alert(
    session,
    transaction_id: int,
    score: float,
    probability: float,
    level: str
):

    alert = FraudAlert(
        transaction_id=transaction_id,
        fraud_score=score,
        fraud_probability=probability,
        risk_level=level
    )

    session.add(alert)

    await session.commit()

    await session.refresh(alert)

    return alert


async def get_alerts(session):

    result = await session.execute(
        select(FraudAlert).order_by(
            FraudAlert.created_at.desc()
        )
    )

    return result.scalars().all()


async def get_alert_by_id(
    session,
    alert_id: int
):

    result = await session.execute(
        select(FraudAlert).where(
            FraudAlert.id == alert_id
        )
    )

    return result.scalar_one_or_none()


async def get_alert_stats(session):

    total_alerts = await session.scalar(
        select(func.count(FraudAlert.id))
    )

    average_probability = await session.scalar(
        select(func.avg(FraudAlert.fraud_probability))
    )

    high_alerts = await session.scalar(
        select(func.count(FraudAlert.id)).where(
            FraudAlert.risk_level == "HIGH"
        )
    )

    medium_alerts = await session.scalar(
        select(func.count(FraudAlert.id)).where(
            FraudAlert.risk_level == "MEDIUM"
        )
    )

    low_alerts = await session.scalar(
        select(func.count(FraudAlert.id)).where(
            FraudAlert.risk_level == "LOW"
        )
    )

    return {
        "total_alerts": total_alerts or 0,
        "high_alerts": high_alerts or 0,
        "medium_alerts": medium_alerts or 0,
        "low_alerts": low_alerts or 0,
        "average_fraud_probability": float(average_probability or 0.0)
    }
