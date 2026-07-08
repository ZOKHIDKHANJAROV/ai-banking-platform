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
        "Published event topic=%s transaction_id=%s user_id=%s",
        topic,
        data.get("transaction_id"),
        data.get("user_id")
    )


async def start_producer():

    global producer

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
    )

    await producer.start()



async def stop_producer():
    if producer is not None:
        await producer.stop()


async def send_transaction_event(data: dict):
    await send_event(
        "transactions",
        data
    )
