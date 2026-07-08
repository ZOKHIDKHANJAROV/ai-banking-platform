from pydantic import BaseModel


class PredictionRequest(BaseModel):
    amount: float
    tx_count: int
    country: str
    previous_country: str | None = None


class PredictionResponse(BaseModel):
    fraud_score: float
    fraud_probability: float
    risk_level: str
