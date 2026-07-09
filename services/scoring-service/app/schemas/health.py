from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    model_source: str | None = None
