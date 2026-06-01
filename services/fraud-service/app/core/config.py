from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str

    REDIS_HOST: str
    REDIS_PORT: int

    class Config:
        env_file = ".env"


settings = Settings()