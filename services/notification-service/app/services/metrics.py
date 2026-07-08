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
    "notification_service_http_requests_total",
    "Total HTTP requests handled by the notification service.",
    ["method", "path", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "notification_service_http_request_duration_seconds",
    "HTTP request latency for the notification service.",
    ["method", "path"],
    registry=registry
)

notifications_created_total = Counter(
    "notification_service_notifications_created_total",
    "Notifications persisted by the notification service.",
    ["channel", "status"],
    registry=registry
)

kafka_worker_retries_total = Counter(
    "notification_service_kafka_worker_retries_total",
    "Kafka worker retries in the notification service.",
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
