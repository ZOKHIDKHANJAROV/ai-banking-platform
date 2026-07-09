from pydantic import BaseModel


class NotificationStatsResponse(BaseModel):
    total_notifications: int
    sent_notifications: int
    failed_notifications: int
    pending_notifications: int
