from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class StoredCreditScoreResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    user_id: int
    credit_score: float
    repayment_probability: float
    score_band: str
    model_source: str
    features_json: str
    created_at: datetime
