from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)

    amount = Column(Float, nullable=False)

    currency = Column(String, default="USD")

    country = Column(String, nullable=False)

    device_type = Column(String, nullable=False)

    status = Column(String, default="PENDING")

    created_at = Column(DateTime(timezone=True), server_default=func.now())