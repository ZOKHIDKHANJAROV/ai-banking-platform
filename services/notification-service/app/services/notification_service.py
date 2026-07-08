from sqlalchemy import func
from sqlalchemy import select

from app.models.notification import Notification
from app.services.metrics import notifications_created_total


RISK_LEVEL_CHANNELS = {
    "HIGH": ("SMS", "+10000000000"),
    "MEDIUM": ("EMAIL", "risk-review@bank.local"),
    "LOW": ("EMAIL", "ops@bank.local"),
}


def build_notification_content(
    alert_event: dict
) -> tuple[str, str, str]:
    channel, recipient = RISK_LEVEL_CHANNELS.get(
        alert_event["risk_level"],
        ("EMAIL", "risk-review@bank.local")
    )
    message = (
        f"Fraud alert {alert_event['alert_id']} for transaction "
        f"{alert_event['transaction_id']} is {alert_event['risk_level']} "
        f"risk with status {alert_event['transaction_status']}."
    )

    return channel, recipient, message


async def save_notification(
    session,
    alert_event: dict
):
    channel, recipient, message = build_notification_content(
        alert_event
    )

    notification = Notification(
        alert_id=alert_event["alert_id"],
        transaction_id=alert_event["transaction_id"],
        channel=channel,
        recipient=recipient,
        message=message,
        status="SENT"
    )

    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    notifications_created_total.labels(
        notification.channel,
        notification.status
    ).inc()

    return notification


async def get_notifications(
    session
):
    result = await session.execute(
        select(Notification).order_by(
            Notification.created_at.desc(),
            Notification.id.desc()
        )
    )

    return result.scalars().all()


async def get_notification_by_id(
    session,
    notification_id: int
):
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id
        )
    )

    return result.scalar_one_or_none()


async def get_notification_stats(
    session
):
    total_notifications = await session.scalar(
        select(func.count(Notification.id))
    )

    sent_notifications = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.status == "SENT"
        )
    )

    return {
        "total_notifications": total_notifications or 0,
        "sent_notifications": sent_notifications or 0
    }
