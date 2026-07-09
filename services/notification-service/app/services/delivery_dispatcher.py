import logging
import uuid
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


class DeliveryDispatcher:
    def __init__(
        self,
        websocket_hub
    ):
        self.websocket_hub = websocket_hub

    async def send(
        self,
        notification
    ) -> str:
        channel = notification.channel.upper()

        if channel == "EMAIL":
            return await self._send_email(
                notification
            )

        if channel == "SMS":
            return await self._send_sms(
                notification
            )

        if channel == "TELEGRAM":
            return await self._send_telegram(
                notification
            )

        if channel == "WEBSOCKET":
            return await self._send_websocket(
                notification
            )

        raise RuntimeError(
            f"Unsupported notification channel: {channel}"
        )

    async def _send_email(
        self,
        notification
    ) -> str:
        import aiosmtplib

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = notification.recipient
        message["Subject"] = (
            f"Fraud alert {notification.alert_id} "
            f"({notification.channel})"
        )
        message.set_content(
            notification.message
        )

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_USE_TLS
        )

        return f"email-{uuid.uuid4()}"

    async def _send_sms(
        self,
        notification
    ) -> str:
        import httpx

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
            response = await client.post(
                settings.SMS_PROVIDER_URL,
                headers={
                    "X-API-Key": settings.SMS_API_KEY
                },
                json={
                    "recipient": notification.recipient,
                    "message": notification.message,
                    "alert_id": notification.alert_id,
                    "transaction_id": notification.transaction_id
                }
            )
            response.raise_for_status()
            data = response.json()

        return data.get(
            "message_id",
            f"sms-{uuid.uuid4()}"
        )

    async def _send_telegram(
        self,
        notification
    ) -> str:
        import httpx

        base_url = settings.TELEGRAM_API_BASE_URL.rstrip("/")
        token = settings.TELEGRAM_BOT_TOKEN
        endpoint = f"{base_url}/bot{token}/sendMessage"

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
            response = await client.post(
                endpoint,
                json={
                    "chat_id": notification.recipient,
                    "text": notification.message
                }
            )
            response.raise_for_status()
            data = response.json()

        result = data.get(
            "result",
            {}
        )

        return str(
            result.get(
                "message_id",
                f"telegram-{uuid.uuid4()}"
            )
        )

    async def _send_websocket(
        self,
        notification
    ) -> str:
        return await self.websocket_hub.broadcast(
            {
                "alert_id": notification.alert_id,
                "transaction_id": notification.transaction_id,
                "channel": notification.channel,
                "recipient": notification.recipient,
                "message": notification.message,
                "status": notification.status
            }
        )
