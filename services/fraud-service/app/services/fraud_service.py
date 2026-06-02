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