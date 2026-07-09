from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.database import Base


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(
        Integer,
        primary_key=True
    )
    transaction_id = Column(
        Integer,
        nullable=False,
        index=True
    )
    fraud_probability = Column(
        Float,
        nullable=False
    )
    risk_level = Column(
        String,
        nullable=False
    )
    model_name = Column(
        String,
        nullable=False
    )
    model_version = Column(
        String,
        nullable=True
    )
    model_role = Column(
        String,
        nullable=False,
        default="CHAMPION"
    )
    is_live_decision = Column(
        Boolean,
        nullable=False,
        default=True
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
