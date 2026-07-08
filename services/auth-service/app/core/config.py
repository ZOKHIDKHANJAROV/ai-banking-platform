from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    AUTH_USERNAME: str
    AUTH_PASSWORD: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "ai-banking-platform"
    JWT_ISSUER: str = "auth-service"
    JWT_EXPIRES_MINUTES: int = 60


settings = Settings()
