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
    created_at: datetime
