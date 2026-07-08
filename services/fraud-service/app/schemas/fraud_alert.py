from datetime import datetime
from pydantic import BaseModel
from pydantic import ConfigDict


class FraudAlertResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    transaction_id: int
    fraud_score: float
    fraud_probability: float
    risk_level: str
    created_at: datetime


class FraudStatsResponse(BaseModel):
    total_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    average_fraud_probability: float
