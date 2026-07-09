from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AssistantQueryRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    question: str = Field(
        min_length=3,
        max_length=4000
    )
    previous_response_id: str | None = None
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=10
    )


class AssistantSource(BaseModel):
    alert_id: int
    transaction_id: int
    risk_level: str
    score: float
    snippet: str
    similarity_score: float


class AssistantQueryResponse(BaseModel):
    answer: str
    assistant_mode: str
    response_id: str | None = None
    previous_response_id: str | None = None
    sources: list[AssistantSource]
