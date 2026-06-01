import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings

consumer = AIOKafkaConsumer(
    "transactions",
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    group_id="fraud-detector"
)


async def start_consumer():

    await consumer.start()

    try:

        async for msg in consumer:

            yield json.loads(
                msg.value.decode("utf-8")
            )

    finally:

        await consumer.stop()