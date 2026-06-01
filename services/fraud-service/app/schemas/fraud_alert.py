from pydantic import BaseModel
from datetime import datetime


class FraudAlertResponse(BaseModel):
    id: int
    transaction_id: int
    fraud_score: float
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True