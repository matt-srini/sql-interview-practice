from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Awaitable, Callable

from fastapi import Request
from fastapi import HTTPException

from exceptions import AppError

logger = logging.getLogger(__name__)


_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request id or '-' when not in a request context."""

    return _request_id_var.get()


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[object]],
):
    """Assign a request_id, log request lifecycle, and attach X-Request-ID.

    - Generates a UUID request_id per request
    - Stores it in `request.state.request_id`
    - Binds it to a contextvar so downstream code can retrieve it
    - Logs incoming requests and unhandled exceptions with request_id
    """

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    token = _request_id_var.set(request_id)
    try:
        client_ip = request.client.host if request.client else "unknown"
        prefix = f"[request_id={request_id}] "
        logger.info(
            "%s%s %s client_ip=%s",
            prefix,
            request.method,
            request.url.path,
            client_ip,
        )
        response = await call_next(request)
        # Ensure the request id is returned to the client.
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%sCompleted %s %s status_code=%s",
            prefix,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
    except (AppError, HTTPException):
        # Expected / user-facing errors are formatted by centralized handlers.
        raise
    except Exception:
        # Log truly unhandled exceptions with request_id; centralized handler formats response.
        prefix = f"[request_id={request_id}] "
        logger.exception("%sUnhandled exception", prefix)
        raise
    finally:
        _request_id_var.reset(token)
