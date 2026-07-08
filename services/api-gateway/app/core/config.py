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
    API_KEY: str = "dev-gateway-key"
    API_KEY_HEADER_NAME: str = "X-API-Key"
    JWT_SECRET: str = "super-secret-jwt-key-with-32-byte-length"
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "ai-banking-platform"
    JWT_ISSUER: str = "auth-service"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    RATE_LIMIT_BACKEND: str = "redis"
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_BATCH_SIZE: int = 50
    KAFKA_STARTUP_MAX_RETRIES: int = 30
    KAFKA_STARTUP_RETRY_DELAY_SECONDS: float = 2.0

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.ALLOWED_ORIGINS.split(",")
            if item.strip()
        ]


settings = Settings()
