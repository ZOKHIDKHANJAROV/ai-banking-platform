from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    FRAUD_ALERTS_TOPIC: str = "fraud-alerts"
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_CONSUMER_RETRY_DELAY_SECONDS: float = 2.0


settings = Settings()
