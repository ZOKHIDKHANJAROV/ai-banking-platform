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
    NOTIFICATION_MAX_DELIVERY_ATTEMPTS: int = 3

    RISK_REVIEW_EMAIL: str = "risk-review@bank.local"
    OPS_EMAIL: str = "ops@bank.local"
    HIGH_RISK_PHONE: str = "+10000000000"
    HIGH_RISK_TELEGRAM_CHAT_ID: str = "1000000000"

    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alerts@bank.local"
    SMTP_USE_TLS: bool = False

    SMS_PROVIDER_URL: str = "http://notification-service:8000/mock/sms"
    SMS_API_KEY: str = "dev-sms-key"

    TELEGRAM_BOT_TOKEN: str = "dev-telegram-token"
    TELEGRAM_API_BASE_URL: str = "http://notification-service:8000/mock/telegram"


settings = Settings()
