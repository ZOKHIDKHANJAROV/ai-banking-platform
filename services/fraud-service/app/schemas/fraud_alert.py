from datetime import datetime

from pydantic import BaseModel


class FraudAlertResponse(BaseModel):

    id: int

    transaction_id: int

    fraud_score: float

    fraud_probability: float

    risk_level: str

    created_at: datetime

    class Config:

        from_attributes = True