from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class TrainingLogResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    experiment_name: str
    model_name: str
    model_version: int | None
    run_id: str | None
    accuracy: float | None
    parameters_json: str
    metrics_json: str
    status: str
    error_message: str | None
    created_at: datetime
