from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str

    REDIS_HOST: str
    REDIS_PORT: int
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MLFLOW_MODEL_NAME: str = "FraudDetectionModel"
    MLFLOW_MODEL_STAGE: str = "latest"
    LOCAL_MODEL_PATH: str = "models_artifacts/model.pkl"

    class Config:
        env_file = ".env"


settings = Settings()
