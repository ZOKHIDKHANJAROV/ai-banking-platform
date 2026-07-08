import logging
import uuid

import jwt
from fastapi import Request
from starlette.responses import JSONResponse

from app.services.metrics import api_gateway_rate_limited_requests_total
from app.services.metrics import api_gateway_unauthorized_requests_total


logger = logging.getLogger(__name__)

PUBLIC_PATH_PREFIXES = (
    "/",
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc"
)


def is_public_path(
    path: str
) -> bool:
    return path in PUBLIC_PATH_PREFIXES


def validate_bearer_token(
    token: str,
    request: Request
) -> str:
    payload = jwt.decode(
        token,
        request.app.state.jwt_secret,
        algorithms=[request.app.state.jwt_algorithm],
        audience=request.app.state.jwt_audience,
        issuer=request.app.state.jwt_issuer
    )
    subject = payload.get("sub")

    if not subject:
        raise jwt.InvalidTokenError(
            "Missing subject"
        )

    return subject


async def request_context_middleware(
    request: Request,
    call_next
):
    request_id = request.headers.get(
        "X-Request-ID"
    ) or str(uuid.uuid4())
    correlation_id = request.headers.get(
        "X-Correlation-ID"
    ) or request_id

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id

    return response


async def security_middleware(
    request: Request,
    call_next
):
    if request.method == "OPTIONS" or is_public_path(
        request.url.path
    ):
        return await call_next(request)

    auth_header = request.headers.get(
        "Authorization",
        ""
    )
    api_key = request.headers.get(
        request.app.state.api_key_header_name
    )
    principal = None

    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix(
            "Bearer "
        ).strip()

        try:
            principal = (
                f"jwt:{validate_bearer_token(token, request)}"
            )
        except jwt.InvalidTokenError:
            api_gateway_unauthorized_requests_total.inc()
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid bearer token"
                }
            )
    elif api_key == request.app.state.api_key:
        principal = f"api-key:{api_key}"
    else:
        api_gateway_unauthorized_requests_total.inc()
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Invalid or missing credentials"
            }
        )

    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = (
        "gateway-rate-limit:"
        f"{principal}:{client_host}:{request.url.path}"
    )

    allowed = await request.app.state.rate_limiter.allow_request(
        rate_limit_key
    )

    if not allowed:
        api_gateway_rate_limited_requests_total.inc()
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            }
        )

    return await call_next(request)
