import json
import logging
from datetime import datetime
from datetime import timezone

from sqlalchemy import select

from app.models.outbox_event import OutboxEvent
from app.models.transaction import Transaction
from app.services.kafka_producer import send_event
from app.services.metrics import outbox_events_dispatched_total
from app.services.metrics import outbox_pending_events

logger = logging.getLogger(__name__)


async def enqueue_transaction_event(
    session,
    transaction: Transaction
):
    event = OutboxEvent(
        transaction_id=transaction.id,
        topic="transactions",
        payload=json.dumps({
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "amount": transaction.amount,
            "country": transaction.country,
            "device_type": transaction.device_type
        }),
        status="PENDING",
        attempts=0
    )

    session.add(event)
    await session.flush()

    return event


async def dispatch_pending_events(
    session,
    batch_size: int = 50
):
    result = await session.execute(
        select(OutboxEvent).where(
            OutboxEvent.status.in_(["PENDING", "FAILED"])
        ).order_by(
            OutboxEvent.created_at.asc(),
            OutboxEvent.id.asc()
        ).limit(batch_size)
    )

    events = result.scalars().all()
    outbox_pending_events.set(
        len(events)
    )
    published_count = 0

    for event in events:
        transaction = await session.get(
            Transaction,
            event.transaction_id
        )

        try:
            event.attempts += 1

            await send_event(
                event.topic,
                json.loads(event.payload)
            )

            event.status = "SENT"
            event.last_error = None
            event.processed_at = datetime.now(timezone.utc)

            if transaction is not None:
                transaction.status = "QUEUED"

            published_count += 1
            outbox_events_dispatched_total.labels(
                "SENT"
            ).inc()
        except Exception as exc:
            event.status = "FAILED"
            event.last_error = str(exc)[:1000]

            if transaction is not None and transaction.status != "QUEUED":
                transaction.status = "PENDING"

            logger.warning(
                "Failed to dispatch outbox event id=%s transaction_id=%s: %s",
                event.id,
                event.transaction_id,
                exc
            )
            outbox_events_dispatched_total.labels(
                "FAILED"
            ).inc()

    await session.commit()
    remaining_pending = sum(
        1 for event in events
        if event.status in ["PENDING", "FAILED"]
    )
    outbox_pending_events.set(
        remaining_pending
    )

    return published_count
