from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class ModelPredictionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    transaction_id: int
    fraud_probability: float
    risk_level: str
    model_name: str
    model_version: str | None
    model_role: str
    is_live_decision: bool
    model_source: str
    features_json: str
    created_at: datetime
