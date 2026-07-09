from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    alert_id: int
    transaction_id: int
    channel: str
    recipient: str
    message: str
    status: str
    attempts: int
    last_error: str | None = None
    provider_message_id: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime
