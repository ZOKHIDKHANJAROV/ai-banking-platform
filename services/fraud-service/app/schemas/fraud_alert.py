from datetime import datetime

from pydantic import BaseModel


class FraudAlertResponse(BaseModel):

    id: int
    transaction_id: int
    score: float
    level: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }