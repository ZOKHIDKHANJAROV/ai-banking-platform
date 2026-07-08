from fastapi import FastAPI
from fastapi import HTTPException

from app.schemas.auth import TokenRequest
from app.schemas.auth import TokenResponse
from app.schemas.health import HealthResponse
from app.services.auth import authenticate_user
from app.services.auth import create_access_token
from app.services.metrics import auth_failures_total
from app.services.metrics import metrics_middleware
from app.services.metrics import metrics_response
from app.services.metrics import tokens_issued_total


app = FastAPI(
    title="Auth Service"
)
app.middleware("http")(metrics_middleware)


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        service="auth-service",
        status="running"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return await root()


@app.post("/token", response_model=TokenResponse)
async def create_token(
    payload: TokenRequest
):
    if not authenticate_user(
        payload.username,
        payload.password
    ):
        auth_failures_total.inc()
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token, expires_in = create_access_token(
        payload.username
    )
    tokens_issued_total.inc()

    return TokenResponse(
        access_token=token,
        expires_in=expires_in
    )


@app.get("/metrics")
async def get_metrics():
    return metrics_response()
