from sqlalchemy import select
from sqlalchemy import func

from app.models.fraud_alert import FraudAlert


async def get_stats(session):

    total = await session.scalar(
        select(
            func.count(FraudAlert.id)
        )
    )

    high = await session.scalar(
        select(
            func.count(FraudAlert.id)
        ).where(
            FraudAlert.risk_level == "HIGH"
        )
    )

    medium = await session.scalar(
        select(
            func.count(FraudAlert.id)
        ).where(
            FraudAlert.risk_level == "MEDIUM"
        )
    )

    low = await session.scalar(
        select(
            func.count(FraudAlert.id)
        ).where(
            FraudAlert.risk_level == "LOW"
        )
    )

    return {
        "total_alerts": total,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low
    }