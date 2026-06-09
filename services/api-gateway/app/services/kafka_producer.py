import json

from aiokafka import AIOKafkaProducer

from app.core.config import settings

producer = None


async def start_producer():

    global producer

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
    )

    await producer.start()
    
    print("Kafka producer started")


async def stop_producer():

    global producer

    if producer is not None:
        await producer.stop()


async def send_transaction_event(
    data: dict
):

    global producer

    if producer is None:
        raise RuntimeError(
            "Kafka producer not initialized"
        )

    await producer.send_and_wait(
        "transactions",
        json.dumps(data).encode("utf-8")
    )