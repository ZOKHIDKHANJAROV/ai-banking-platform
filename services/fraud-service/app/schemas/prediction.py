from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


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
    model_config = ConfigDict(
        ser_json_exclude_none=True
    )

    fraud_score: float
    fraud_probability: float
    risk_level: str
    decision_model_role: str = "CHAMPION"
    challenger_fraud_probability: float | None = None
    challenger_risk_level: str | None = None
    probability_delta: float | None = None
