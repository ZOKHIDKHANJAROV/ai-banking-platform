from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.database import Base


class TrainingLog(Base):
    __tablename__ = "training_logs"

    id = Column(
        Integer,
        primary_key=True
    )
    experiment_name = Column(
        String,
        nullable=False
    )
    model_name = Column(
        String,
        nullable=False,
        index=True
    )
    model_version = Column(
        Integer,
        nullable=True
    )
    run_id = Column(
        String,
        nullable=True,
        index=True
    )
    accuracy = Column(
        Float,
        nullable=True
    )
    parameters_json = Column(
        Text,
        nullable=False
    )
    metrics_json = Column(
        Text,
        nullable=False
    )
    status = Column(
        String,
        nullable=False
    )
    error_message = Column(
        Text,
        nullable=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
