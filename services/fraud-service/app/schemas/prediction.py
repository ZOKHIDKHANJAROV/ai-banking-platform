from datetime import datetime

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    amount: float
    tx_count: int
    country: str
    device_type: str = "web"
    previous_country: str | None = None
    previous_amount: float | None = None
    previous_device_type: str | None = None
    transaction_at: datetime | None = None


class PredictionResponse(BaseModel):
    fraud_score: float
    fraud_probability: float
    risk_level: str
