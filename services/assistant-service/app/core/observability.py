from __future__ import annotations

import contextvars
import json
import logging
import sys
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
from logging.config import dictConfig
from uuid import uuid4

from fastapi import Request


request_id_var = contextvars.ContextVar(
    "request_id",
    default=None
)
correlation_id_var = contextvars.ContextVar(
    "correlation_id",
    default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "assistant-service"),
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_var.get()
        correlation_id = correlation_id_var.get()

        if request_id:
            payload["request_id"] = request_id
        if correlation_id:
            payload["correlation_id"] = correlation_id

        for key in (
            "event",
            "collection_name",
            "indexed_count",
            "assistant_mode",
            "query_top_k",
            "response_id",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        return json.dumps(payload)


def configure_logging(
    service_name: str
) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "json",
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )

    logging.LoggerAdapter(
        logging.getLogger(),
        {"service": service_name}
    )


async def request_context_middleware(
    request: Request,
    call_next
):
    request_id = request.headers.get(
        "X-Request-ID"
    ) or str(uuid4())
    correlation_id = request.headers.get(
        "X-Correlation-ID"
    ) or request_id

    request_id_token = request_id_var.set(
        request_id
    )
    correlation_id_token = correlation_id_var.set(
        correlation_id
    )

    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(request_id_token)
        correlation_id_var.reset(correlation_id_token)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id

    return response


@contextmanager
def event_log_context(
    payload: dict
):
    request_id = payload.get(
        "request_id"
    )
    correlation_id = payload.get(
        "correlation_id"
    )

    request_token = None
    correlation_token = None

    if request_id:
        request_token = request_id_var.set(
            request_id
        )
    if correlation_id:
        correlation_token = correlation_id_var.set(
            correlation_id
        )

    try:
        yield
    finally:
        if request_token is not None:
            request_id_var.reset(request_token)
        if correlation_token is not None:
            correlation_id_var.reset(correlation_token)
