import asyncio

from app.core.config import settings


class OpenAIService:
    def __init__(self):
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(
            settings.OPENAI_API_KEY
        )

    def get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY
            )

        return self._client

    async def embed_texts(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        if not self.is_configured:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured"
            )

        client = self.get_client()
        response = await asyncio.to_thread(
            client.embeddings.create,
            input=texts,
            model=settings.OPENAI_EMBEDDING_MODEL
        )

        return [
            item.embedding
            for item in response.data
        ]

    async def generate_answer(
        self,
        *,
        question: str,
        context_blocks: list[str],
        previous_response_id: str | None = None
    ) -> tuple[str, str | None]:
        if not self.is_configured:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured"
            )

        client = self.get_client()
        response = await asyncio.to_thread(
            client.responses.create,
            model=settings.OPENAI_RESPONSE_MODEL,
            instructions=(
                "You are a fraud investigation assistant for a banking platform. "
                "Answer only from the provided fraud history context. "
                "If the retrieved context is insufficient, say so clearly."
            ),
            input=(
                "Retrieved fraud history context:\n\n"
                + "\n\n---\n\n".join(context_blocks)
                + "\n\nUser question:\n"
                + question
            ),
            previous_response_id=previous_response_id,
            store=settings.OPENAI_STORE_RESPONSES
        )

        return response.output_text, response.id


openai_service = OpenAIService()
