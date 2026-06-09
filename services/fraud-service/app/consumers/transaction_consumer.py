import json
import asyncio

from aiokafka import AIOKafkaConsumer


async def start_consumer():

    consumer = AIOKafkaConsumer(
        "transactions",
        bootstrap_servers="kafka:9092",
        group_id="fraud-service",
        auto_offset_reset="earliest"
    )

    while True:

        try:

            print("Connecting to Kafka...")

            await consumer.start()

            print("Kafka consumer connected")

            break

        except Exception as e:

            print(
                f"Kafka unavailable: {e}"
            )

            await asyncio.sleep(5)

    try:

        async for msg in consumer:

            transaction = json.loads(
                msg.value.decode("utf-8")
            )

            print(
                f"Message received: {transaction}"
            )

            yield transaction

    finally:

        await consumer.stop()