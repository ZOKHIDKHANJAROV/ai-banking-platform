import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException

from app.core.observability import configure_logging
from app.core.observability import request_context_middleware
from app.db.database import AsyncSessionLocal
from app.db.database import Base
from app.db.database import engine
from app.schemas.health import HealthResponse
from app.schemas.score import CreditScoreRequest
from app.schemas.score import CreditScoreResponse
from app.schemas.stored_score import StoredCreditScoreResponse
from app.services.credit_score_service import get_score_by_id
from app.services.credit_score_service import get_scores
from app.services.credit_score_service import save_credit_score
from app.services.metrics import metrics_middleware
from app.services.metrics import metrics_response
from app.services.ml_credit_engine import score_credit
from app.services.model_loader import model_loader


configure_logging("scoring-service")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    model_loader.load()

    yield


app = FastAPI(
    title="Credit Scoring Service",
    lifespan=lifespan
)
app.middleware("http")(request_context_middleware)
app.middleware("http")(metrics_middleware)


@app.get("/", response_model=HealthResponse)
async def root():
    return await health()


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        service="scoring-service",
        status="running",
        model_source=model_loader.source
    )


@app.post("/score", response_model=CreditScoreResponse)
async def create_score(
    payload: CreditScoreRequest
):
    features, repayment_probability, credit_score, score_band = score_credit(
        age=payload.age,
        monthly_income=payload.monthly_income,
        existing_debt=payload.existing_debt,
        credit_history_months=payload.credit_history_months,
        delinquency_count=payload.delinquency_count,
        utilization_ratio=payload.utilization_ratio,
        active_loans=payload.active_loans
    )

    async with AsyncSessionLocal() as session:
        stored_score = await save_credit_score(
            session=session,
            user_id=payload.user_id,
            credit_score=credit_score,
            repayment_probability=repayment_probability,
            score_band=score_band,
            model_source=model_loader.source,
            features=features.iloc[0].to_dict()
        )

    logger.info(
        "Generated credit score",
        extra={
            "event": "scoring.score.generated",
            "user_id": payload.user_id,
            "score_band": score_band
        }
    )

    return CreditScoreResponse(
        user_id=stored_score.user_id,
        credit_score=stored_score.credit_score,
        repayment_probability=stored_score.repayment_probability,
        score_band=stored_score.score_band
    )


@app.get(
    "/scores",
    response_model=list[StoredCreditScoreResponse]
)
async def read_scores():
    async with AsyncSessionLocal() as session:
        return await get_scores(
            session
        )


@app.get(
    "/scores/{score_id}",
    response_model=StoredCreditScoreResponse
)
async def read_score(
    score_id: int
):
    async with AsyncSessionLocal() as session:
        score = await get_score_by_id(
            session,
            score_id
        )

        if score is None:
            raise HTTPException(
                status_code=404,
                detail="Credit score not found"
            )

        return score


@app.get("/metrics")
async def get_metrics():
    return metrics_response()
