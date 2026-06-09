from sqlalchemy import (
    Integer,
    Float,
    String,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from datetime import datetime

from app.db.database import Base


class FraudAlert(Base):

    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    transaction_id: Mapped[int]

    score: Mapped[float]

    level: Mapped[str] = mapped_column(
        String(20)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )