from pydantic import BaseModel
from pydantic import Field


class ReindexRequest(BaseModel):
    limit: int | None = Field(
        default=None,
        ge=1,
        le=5000
    )


class ReindexResponse(BaseModel):
    collection_name: str
    indexed_count: int


class KnowledgeStatsResponse(BaseModel):
    collection_name: str
    indexed_vectors: int
