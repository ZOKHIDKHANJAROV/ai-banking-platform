import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings


logger = logging.getLogger(__name__)

producer = None


async def send_event(
    topic: str,
    data: dict
):
    if producer is None:
        raise RuntimeError(
            "Kafka producer not initialized"
        )

    await producer.send_and_wait(
        topic,
        json.dumps(data).encode("utf-8")
    )

    logger.info(
        "Published event topic=%s alert_id=%s transaction_id=%s",
        topic,
        data.get("alert_id"),
        data.get("transaction_id"),
        extra={
            "event": "fraud.kafka.published",
            "alert_id": data.get("alert_id"),
            "transaction_id": data.get("transaction_id"),
            "risk_level": data.get("risk_level")
        }
    )


async def start_producer():
    global producer

    last_error = None

    for attempt in range(
        1,
        settings.KAFKA_PRODUCER_STARTUP_MAX_RETRIES + 1
    ):
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )

        try:
            await producer.start()
            logger.info(
                "Fraud-service Kafka producer started on attempt %s",
                attempt
            )
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Fraud-service Kafka producer startup attempt %s/%s failed: %s",
                attempt,
                settings.KAFKA_PRODUCER_STARTUP_MAX_RETRIES,
                exc
            )
            await producer.stop()
            producer = None
            await asyncio.sleep(
                settings.KAFKA_PRODUCER_STARTUP_RETRY_DELAY_SECONDS
            )

    raise last_error


async def stop_producer():
    global producer

    if producer is not None:
        await producer.stop()
        producer = None


async def send_fraud_alert_event(data: dict):
    await send_event(
        settings.FRAUD_ALERTS_TOPIC,
        data
    )
