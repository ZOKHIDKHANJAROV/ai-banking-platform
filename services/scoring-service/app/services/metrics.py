import time

from fastapi import Request
from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest
from starlette.responses import Response


registry = CollectorRegistry()

http_requests_total = Counter(
    "scoring_service_http_requests_total",
    "Total HTTP requests handled by the scoring service.",
    ["method", "path", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "scoring_service_http_request_duration_seconds",
    "HTTP request latency for the scoring service.",
    ["method", "path"],
    registry=registry
)

credit_scores_generated_total = Counter(
    "scoring_service_credit_scores_generated_total",
    "Credit scores produced by the scoring service.",
    ["score_band"],
    registry=registry
)

last_credit_score_value = Gauge(
    "scoring_service_last_credit_score_value",
    "Last generated credit score.",
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
