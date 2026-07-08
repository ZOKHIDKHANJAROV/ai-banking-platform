from pydantic import BaseModel
from datetime import datetime


class FraudAlertResponse(BaseModel):
    id: int
    transaction_id: int
    fraud_score: float
    fraud_probability: float
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class FraudStatsResponse(BaseModel):
    total_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    average_fraud_probability: float
