from datetime import datetime
from datetime import timezone

from sqlalchemy import func
from sqlalchemy import select

from app.core.config import settings
from app.models.notification import Notification
from app.services.metrics import notifications_created_total


RISK_LEVEL_CHANNELS = {
    "HIGH": [
        ("SMS", settings.HIGH_RISK_PHONE),
        ("TELEGRAM", settings.HIGH_RISK_TELEGRAM_CHAT_ID),
        ("WEBSOCKET", "fraud-ops-live")
    ],
    "MEDIUM": [
        ("EMAIL", settings.RISK_REVIEW_EMAIL),
        ("WEBSOCKET", "fraud-ops-live")
    ],
    "LOW": [
        ("EMAIL", settings.OPS_EMAIL)
    ]
}


def build_notification_message(
    alert_event: dict
) -> str:
    return (
        f"Fraud alert {alert_event['alert_id']} for transaction "
        f"{alert_event['transaction_id']} is {alert_event['risk_level']} "
        f"risk with status {alert_event['transaction_status']}."
    )


def build_notification_deliveries(
    alert_event: dict
) -> list[dict]:
    deliveries = RISK_LEVEL_CHANNELS.get(
        alert_event["risk_level"],
        [("EMAIL", settings.RISK_REVIEW_EMAIL)]
    )
    message = build_notification_message(
        alert_event
    )

    return [
        {
            "channel": channel,
            "recipient": recipient,
            "message": message
        }
        for channel, recipient in deliveries
    ]


async def create_notification(
    session,
    *,
    alert_event: dict,
    channel: str,
    recipient: str,
    message: str
):
    notification = Notification(
        alert_id=alert_event["alert_id"],
        transaction_id=alert_event["transaction_id"],
        channel=channel,
        recipient=recipient,
        message=message,
        status="PENDING",
        attempts=0
    )

    session.add(notification)
    await session.flush()
    await session.commit()
    await session.refresh(notification)

    return notification


async def deliver_notification(
    session,
    *,
    notification: Notification,
    dispatcher
):
    notification.attempts += 1

    try:
        provider_message_id = await dispatcher.send(
            notification
        )
        notification.status = "SENT"
        notification.last_error = None
        notification.provider_message_id = provider_message_id
        notification.delivered_at = datetime.now(
            timezone.utc
        )
    except Exception as exc:
        notification.status = "FAILED"
        notification.last_error = str(exc)[:1000]

        if notification.attempts >= settings.NOTIFICATION_MAX_DELIVERY_ATTEMPTS:
            notification.status = "FAILED"

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
    failed_notifications = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.status == "FAILED"
        )
    )
    pending_notifications = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.status == "PENDING"
        )
    )

    return {
        "total_notifications": total_notifications or 0,
        "sent_notifications": sent_notifications or 0,
        "failed_notifications": failed_notifications or 0,
        "pending_notifications": pending_notifications or 0
    }


async def retry_notification(
    session,
    *,
    notification_id: int,
    dispatcher
):
    notification = await get_notification_by_id(
        session,
        notification_id
    )

    if notification is None:
        return None

    return await deliver_notification(
        session,
        notification=notification,
        dispatcher=dispatcher
    )
