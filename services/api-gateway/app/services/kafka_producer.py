import json

from aiokafka import AIOKafkaProducer

from app.core.config import settings

producer = AIOKafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
)


async def start_producer():
    await producer.start()


async def stop_producer():
    await producer.stop()


async def send_transaction_event(data: dict):
    await producer.send_and_wait(
        "transactions",
        json.dumps(data).encode("utf-8")
    )