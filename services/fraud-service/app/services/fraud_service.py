from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud_alert import FraudAlert


async def save_alert(
    session: AsyncSession,
    transaction_id: int,
    fraud_score: float,
    fraud_probability: float,
    risk_level: str
):

    alert = FraudAlert(
        transaction_id=transaction_id,
        fraud_score=fraud_score,
        fraud_probability=fraud_probability,
        risk_level=risk_level
    )

    session.add(alert)

    await session.commit()

    await session.refresh(alert)

    return alert


async def get_alerts(
    session: AsyncSession
):

    result = await session.execute(
        select(FraudAlert)
        .order_by(FraudAlert.id.desc())
    )

    return result.scalars().all()


async def get_alert_by_id(
    session: AsyncSession,
    alert_id: int
):

    result = await session.execute(
        select(FraudAlert)
        .where(FraudAlert.id == alert_id)
    )

    return result.scalar_one_or_none()