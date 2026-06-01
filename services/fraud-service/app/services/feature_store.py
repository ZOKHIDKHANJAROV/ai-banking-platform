from app.db.redis import redis_client


async def save_last_transaction(
    user_id: int,
    amount: float
):
    await redis_client.set(
        f"user:{user_id}:last_amount",
        amount
    )


async def get_last_transaction(
    user_id: int
):
    return await redis_client.get(
        f"user:{user_id}:last_amount"
    )


async def increment_transaction_count(
    user_id: int
):
    key = f"user:{user_id}:tx_count"

    count = await redis_client.incr(key)

    await redis_client.expire(
        key,
        3600
    )

    return count


async def get_transaction_count(
    user_id: int
):
    value = await redis_client.get(
        f"user:{user_id}:tx_count"
    )

    if value is None:
        return 0

    return int(value)


async def save_country(
    user_id: int,
    country: str
):
    await redis_client.set(
        f"user:{user_id}:country",
        country
    )


async def get_country(
    user_id: int
):
    return await redis_client.get(
        f"user:{user_id}:country"
    )