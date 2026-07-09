from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    assistant_mode: str
    qdrant_collection: str
