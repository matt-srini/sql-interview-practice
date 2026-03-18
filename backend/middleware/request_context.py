from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse

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
        logger.info(
            f"[request_id={request_id}] "
            f"{request.method} {request.url.path} "
            f"client_ip={client_ip}"
        )
        response = await call_next(request)
        # Ensure the request id is returned to the client.
        response.headers["X-Request-ID"] = request_id
        logger.info(
            f"[request_id={request_id}] "
            f"Completed {request.method} {request.url.path} "
            f"status_code={response.status_code}"
        )
        return response
    except Exception:
        # Log unhandled exception with request_id, but do not leak traces to the client.
        logger.exception(
            f"[request_id={request_id}] Unhandled exception"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
    finally:
        _request_id_var.reset(token)
