from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str

    REDIS_HOST: str
    REDIS_PORT: int
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_BATCH_SIZE: int = 50
    KAFKA_STARTUP_MAX_RETRIES: int = 30
    KAFKA_STARTUP_RETRY_DELAY_SECONDS: float = 2.0


settings = Settings()
