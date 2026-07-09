import contextvars
from datetime import datetime
from datetime import timezone
import json
import logging
import sys
import uuid

from fastapi import Request


request_id_var = contextvars.ContextVar(
    "request_id",
    default=None
)
correlation_id_var = contextvars.ContextVar(
    "correlation_id",
    default=None
)
service_name_var = contextvars.ContextVar(
    "service_name",
    default="unknown"
)


class JsonFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord
    ) -> str:
        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": getattr(
                record,
                "service",
                service_name_var.get()
            ),
            "logger": record.name,
            "message": record.getMessage()
        }

        request_id = getattr(
            record,
            "request_id",
            None
        ) or request_id_var.get()
        correlation_id = getattr(
            record,
            "correlation_id",
            None
        ) or correlation_id_var.get()

        if request_id is not None:
            payload["request_id"] = request_id

        if correlation_id is not None:
            payload["correlation_id"] = correlation_id

        for field_name in [
            "event",
            "method",
            "path",
            "status_code",
            "principal"
        ]:
            value = getattr(
                record,
                field_name,
                None
            )

            if value is not None:
                payload[field_name] = value

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            ensure_ascii=True
        )


def configure_logging(
    service_name: str
) -> None:
    service_name_var.set(service_name)
    handler = logging.StreamHandler(
        sys.stdout
    )
    handler.setFormatter(
        JsonFormatter()
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(
        handler
    )
    root_logger.setLevel(
        logging.INFO
    )


def set_log_context(
    *,
    request_id: str | None,
    correlation_id: str | None
):
    return (
        request_id_var.set(request_id),
        correlation_id_var.set(correlation_id)
    )


def reset_log_context(
    tokens
) -> None:
    request_id_token, correlation_id_token = tokens
    request_id_var.reset(
        request_id_token
    )
    correlation_id_var.reset(
        correlation_id_token
    )


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
    tokens = set_log_context(
        request_id=request_id,
        correlation_id=correlation_id
    )

    try:
        response = await call_next(request)
    finally:
        reset_log_context(tokens)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id

    return response
