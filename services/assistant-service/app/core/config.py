from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    DATABASE_URL: str
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION_NAME: str = "fraud_assistant_memory"

    OPENAI_API_KEY: str | None = None
    OPENAI_RESPONSE_MODEL: str = "gpt-5.4-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_STORE_RESPONSES: bool = True

    ASSISTANT_TOP_K: int = 5
    ASSISTANT_REINDEX_LIMIT: int = 500


settings = Settings()
