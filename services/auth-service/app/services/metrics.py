import time

from fastapi import Request
from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Histogram
from prometheus_client import generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import Response


registry = CollectorRegistry()

http_requests_total = Counter(
    "auth_service_http_requests_total",
    "Total HTTP requests handled by the auth service.",
    ["method", "path", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "auth_service_http_request_duration_seconds",
    "HTTP request latency for the auth service.",
    ["method", "path"],
    registry=registry
)

tokens_issued_total = Counter(
    "auth_service_tokens_issued_total",
    "JWT access tokens issued by the auth service.",
    registry=registry
)

auth_failures_total = Counter(
    "auth_service_auth_failures_total",
    "Failed authentication attempts in the auth service.",
    registry=registry
)


async def metrics_middleware(
    request: Request,
    call_next
):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time
    path = request.url.path

    http_requests_total.labels(
        request.method,
        path,
        str(response.status_code)
    ).inc()
    http_request_duration_seconds.labels(
        request.method,
        path
    ).observe(duration)

    return response


def metrics_response() -> Response:
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )
