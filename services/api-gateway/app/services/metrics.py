import time

from fastapi import Request
from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import Response


registry = CollectorRegistry()

http_requests_total = Counter(
    "api_gateway_http_requests_total",
    "Total HTTP requests handled by the API gateway.",
    ["method", "path", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "api_gateway_http_request_duration_seconds",
    "HTTP request latency for the API gateway.",
    ["method", "path"],
    registry=registry
)

transactions_created_total = Counter(
    "api_gateway_transactions_created_total",
    "Transactions created through the API gateway.",
    ["status"],
    registry=registry
)

outbox_events_dispatched_total = Counter(
    "api_gateway_outbox_events_dispatched_total",
    "Outbox event dispatch attempts from the API gateway.",
    ["status"],
    registry=registry
)

outbox_pending_events = Gauge(
    "api_gateway_outbox_pending_events",
    "Current number of pending or failed outbox events.",
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
