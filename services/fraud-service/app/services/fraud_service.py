from sqlalchemy import select

from app.models.fraud_alert import (
    FraudAlert
)


async def save_alert(
    session,
    transaction_id: int,
    score: float,
    level: str
):

    alert = FraudAlert(
        transaction_id=transaction_id,
        score=score,
        level=level
    )

    session.add(alert)

    await session.commit()

    await session.refresh(alert)

    return alert


async def get_alerts(
    session
):

    result = await session.execute(
        select(FraudAlert)
    )

    return result.scalars().all()

from sqlalchemy import select

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