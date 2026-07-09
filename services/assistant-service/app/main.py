import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.observability import configure_logging
from app.core.observability import event_log_context
from app.core.observability import request_context_middleware
from app.db.database import AsyncSessionLocal
from app.schemas.assistant import AssistantQueryRequest
from app.schemas.assistant import AssistantQueryResponse
from app.schemas.assistant import AssistantSource
from app.schemas.health import HealthResponse
from app.schemas.knowledge import KnowledgeStatsResponse
from app.schemas.knowledge import ReindexRequest
from app.schemas.knowledge import ReindexResponse
from app.services.assistant_service import answer_question
from app.services.assistant_service import build_index_documents
from app.services.history_repository import FraudKnowledgeRecord
from app.services.history_repository import fetch_fraud_knowledge_records
from app.services.metrics import assistant_queries_total
from app.services.metrics import assistant_reindex_total
from app.services.metrics import metrics_middleware
from app.services.metrics import metrics_response
from app.services.openai_service import openai_service
from app.services.qdrant_store import qdrant_store


configure_logging("assistant-service")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await qdrant_store.ensure_collection()
    logger.info(
        "Assistant Service started",
        extra={
            "event": "assistant.startup"
        }
    )
    yield


app = FastAPI(
    title="Fraud Assistant Service",
    lifespan=lifespan
)
app.middleware("http")(request_context_middleware)
app.middleware("http")(metrics_middleware)


def current_assistant_mode() -> str:
    if openai_service.is_configured:
        return "llm_retrieval"
    return "retrieval_only"


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        service="assistant-service",
        status="running",
        assistant_mode=current_assistant_mode(),
        qdrant_collection=settings.QDRANT_COLLECTION_NAME
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return await root()


@app.post(
    "/knowledge/reindex",
    response_model=ReindexResponse
)
async def reindex_knowledge(
    payload: ReindexRequest
):
    limit = payload.limit or settings.ASSISTANT_REINDEX_LIMIT

    async with AsyncSessionLocal() as session:
        records = await fetch_fraud_knowledge_records(
            session,
            limit=limit
        )

    documents = await build_index_documents(
        records
    )
    await qdrant_store.upsert_documents(
        documents
    )
    assistant_reindex_total.inc()

    logger.info(
        "Indexed fraud history into Qdrant",
        extra={
            "event": "assistant.knowledge.reindexed",
            "collection_name": settings.QDRANT_COLLECTION_NAME,
            "indexed_count": len(documents)
        }
    )

    return ReindexResponse(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        indexed_count=len(documents)
    )


@app.get(
    "/knowledge/stats",
    response_model=KnowledgeStatsResponse
)
async def get_knowledge_stats():
    indexed_vectors = await qdrant_store.count()
    return KnowledgeStatsResponse(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        indexed_vectors=indexed_vectors
    )


@app.post(
    "/assistant/query",
    response_model=AssistantQueryResponse
)
async def query_assistant(
    payload: AssistantQueryRequest
):
    with event_log_context(
        {
            "request_id": None,
            "correlation_id": None
        }
    ):
        top_k = payload.top_k or settings.ASSISTANT_TOP_K
        result = await answer_question(
            question=payload.question,
            previous_response_id=payload.previous_response_id,
            top_k=top_k
        )

    assistant_queries_total.labels(
        result["assistant_mode"]
    ).inc()
    logger.info(
        "Answered assistant query",
        extra={
            "event": "assistant.query.completed",
            "assistant_mode": result["assistant_mode"],
            "query_top_k": top_k,
            "response_id": result["response_id"]
        }
    )

    return AssistantQueryResponse(
        answer=result["answer"],
        assistant_mode=result["assistant_mode"],
        response_id=result["response_id"],
        previous_response_id=payload.previous_response_id,
        sources=[
            AssistantSource(
                alert_id=item["alert_id"],
                transaction_id=item["transaction_id"],
                risk_level=item["risk_level"],
                score=item["score"],
                snippet=item["snippet"],
                similarity_score=item["similarity_score"]
            )
            for item in result["sources"]
        ]
    )


@app.get("/metrics")
async def get_metrics():
    return metrics_response()
