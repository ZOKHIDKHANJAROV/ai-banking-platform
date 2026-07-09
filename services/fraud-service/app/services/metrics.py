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
    "fraud_service_http_requests_total",
    "Total HTTP requests handled by the fraud service.",
    ["method", "path", "status_code"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "fraud_service_http_request_duration_seconds",
    "HTTP request latency for the fraud service.",
    ["method", "path"],
    registry=registry
)

transactions_processed_total = Counter(
    "fraud_service_transactions_processed_total",
    "Transactions processed by the fraud service.",
    ["risk_level", "transaction_status"],
    registry=registry
)

alerts_published_total = Counter(
    "fraud_service_alerts_published_total",
    "Fraud alert events published by the fraud service.",
    ["risk_level"],
    registry=registry
)

kafka_worker_retries_total = Counter(
    "fraud_service_kafka_worker_retries_total",
    "Kafka worker retries in the fraud service.",
    registry=registry
)

model_prediction_probability = Gauge(
    "fraud_service_last_prediction_probability",
    "Last fraud probability produced by the fraud service.",
    registry=registry
)

model_predictions_total = Counter(
    "fraud_service_model_predictions_total",
    "Stored model predictions by model role and risk level.",
    ["model_role", "risk_level", "decision_mode"],
    registry=registry
)

champion_challenger_probability_delta = Histogram(
    "fraud_service_champion_challenger_probability_delta",
    "Absolute probability delta between champion and challenger models.",
    registry=registry
)

champion_challenger_disagreements_total = Counter(
    "fraud_service_champion_challenger_disagreements_total",
    "Disagreements between champion and challenger risk levels.",
    ["champion_risk_level", "challenger_risk_level"],
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
