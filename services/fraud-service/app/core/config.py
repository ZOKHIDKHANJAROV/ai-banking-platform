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
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MLFLOW_MODEL_NAME: str = "FraudDetectionModel"
    MLFLOW_MODEL_STAGE: str = "latest"
    FRAUD_ALERTS_TOPIC: str = "fraud-alerts"
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_CONSUMER_RETRY_DELAY_SECONDS: float = 2.0
    KAFKA_PRODUCER_STARTUP_MAX_RETRIES: int = 30
    KAFKA_PRODUCER_STARTUP_RETRY_DELAY_SECONDS: float = 2.0


settings = Settings()
