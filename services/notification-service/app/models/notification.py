from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    channel = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    provider_message_id = Column(String, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
