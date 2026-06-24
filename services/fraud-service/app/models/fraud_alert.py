from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime
)

from sqlalchemy.sql import func

from app.db.database import Base


class FraudAlert(Base):

    __tablename__ = "fraud_alerts"

    id = Column(
        Integer,
        primary_key=True
    )

    transaction_id = Column(
        Integer
    )

    fraud_score = Column(
        Float
    )

    fraud_probability = Column(
        Float,
        nullable=False
    )

    risk_level = Column(
        String
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )