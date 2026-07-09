from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    DATABASE_URL: str
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MLFLOW_MODEL_NAME: str = "CreditScoringModel"
    MLFLOW_MODEL_STAGE: str = "latest"


settings = Settings()
