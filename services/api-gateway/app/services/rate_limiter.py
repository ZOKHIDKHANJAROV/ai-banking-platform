import asyncio
import time
from collections import deque

from redis import asyncio as redis_asyncio


class InMemoryRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow_request(
        self,
        key: str
    ) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            entries = self._requests.setdefault(
                key,
                deque()
            )

            while entries and entries[0] <= cutoff:
                entries.popleft()

            if len(entries) >= self.limit:
                return False

            entries.append(now)
            return True

    async def close(self):
        return None


class RedisRateLimiter:
    def __init__(
        self,
        client,
        limit: int,
        window_seconds: int
    ):
        self.client = client
        self.limit = limit
        self.window_seconds = window_seconds

    async def allow_request(
        self,
        key: str
    ) -> bool:
        current = await self.client.incr(key)

        if current == 1:
            await self.client.expire(
                key,
                self.window_seconds
            )

        return current <= self.limit

    async def close(self):
        await self.client.aclose()


async def create_rate_limiter(
    settings
):
    if settings.RATE_LIMIT_BACKEND == "memory":
        return InMemoryRateLimiter(
            settings.RATE_LIMIT_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS
        )

    client = redis_asyncio.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    await client.ping()

    return RedisRateLimiter(
        client,
        settings.RATE_LIMIT_REQUESTS,
        settings.RATE_LIMIT_WINDOW_SECONDS
    )
