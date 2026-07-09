import asyncio

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings


class QdrantStore:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL
        )

    async def ensure_collection(self) -> None:
        exists = await asyncio.to_thread(
            self.client.collection_exists,
            settings.QDRANT_COLLECTION_NAME
        )

        if exists:
            return

        await asyncio.to_thread(
            self.client.create_collection,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.OPENAI_EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE
            )
        )

    async def upsert_documents(
        self,
        documents: list[dict]
    ) -> None:
        points = [
            models.PointStruct(
                id=document["id"],
                vector=document["vector"],
                payload=document["payload"]
            )
            for document in documents
        ]

        await asyncio.to_thread(
            self.client.upsert,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points
        )

    async def search(
        self,
        *,
        query_vector: list[float],
        limit: int
    ):
        response = await asyncio.to_thread(
            self.client.query_points,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            with_payload=True
        )
        return response.points

    async def count(self) -> int:
        result = await asyncio.to_thread(
            self.client.count,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            exact=True
        )
        return result.count


qdrant_store = QdrantStore()
