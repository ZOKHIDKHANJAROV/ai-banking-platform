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
    LOCAL_MODEL_PATH: str = "models_artifacts/model.pkl"


settings = Settings()
