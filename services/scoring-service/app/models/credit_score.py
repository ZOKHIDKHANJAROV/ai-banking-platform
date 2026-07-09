from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.database import Base


class CreditScore(Base):
    __tablename__ = "credit_scores"

    id = Column(
        Integer,
        primary_key=True
    )
    user_id = Column(
        Integer,
        nullable=False,
        index=True
    )
    credit_score = Column(
        Float,
        nullable=False
    )
    repayment_probability = Column(
        Float,
        nullable=False
    )
    score_band = Column(
        String,
        nullable=False
    )
    model_source = Column(
        String,
        nullable=False
    )
    features_json = Column(
        Text,
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
