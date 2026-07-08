import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings


def create_consumer():
    return AIOKafkaConsumer(
        settings.FRAUD_ALERTS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification-dispatcher",
        auto_offset_reset=settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET
    )


async def start_consumer():
    consumer = create_consumer()

    await consumer.start()

    try:
        async for msg in consumer:
            yield json.loads(
                msg.value.decode("utf-8")
            )
    finally:
        await consumer.stop()
