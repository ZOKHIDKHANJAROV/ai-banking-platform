import json
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)

producer = None


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

    if producer is None:
        raise RuntimeError(
            "Kafka producer not initialized"
        )

    await producer.send_and_wait(
        "transactions",
        json.dumps(data).encode("utf-8")
    )

    logger.info(
        "Published transaction event transaction_id=%s user_id=%s",
        data.get("transaction_id"),
        data.get("user_id")
    )
