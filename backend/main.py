import logging
import secrets
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, APP_BASE_URL, FRONTEND_BASE_URL, IS_PROD, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, REDIS_URL
from database import close_query_engine, init_query_engine
from db import close_pool, ensure_schema, init_pool
from deps import CSRF_COOKIE_NAME, set_csrf_cookie
from exceptions import AppError
from middleware.request_context import get_request_id, request_context_middleware
from rate_limiter import BaseRateLimiter, create_rate_limiter
from routers import auth, catalog, questions, sample, spa, system
from routers import plan
from routers import razorpay as razorpay_router
from routers import python_questions as python_questions_router
from routers import python_data_questions as python_data_questions_router
from routers import pyspark_questions as pyspark_questions_router
from routers import dashboard as dashboard_router
from routers import insights as insights_router
from routers import submissions as submissions_router
from routers import mock as mock_router
from routers import paths as paths_router
from sentry_utils import init_sentry


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

_root_logger = logging.getLogger()
_formatter = logging.Formatter(LOG_FORMAT)
for _handler in _root_logger.handlers:
    _handler.setFormatter(_formatter)

logger = logging.getLogger(__name__)


init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_query_engine()
    await init_pool()
    if not IS_PROD:
        # In dev/staging, auto-apply schema so developers don't need to run
        # migrations manually.  Swallow connection errors so the app still
        # starts (and reports unhealthy via /health) when the DB isn't yet
        # reachable — e.g. a Railway deploy where DATABASE_URL isn't set yet.
        try:
            await ensure_schema()
        except Exception as exc:
            logger.warning(
                "ensure_schema skipped — database not reachable at startup: %s", exc
            )
    yield
    close_query_engine()
    await close_pool()


app = FastAPI(title="SQL Interview Practice API", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    request_id = get_request_id()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = get_request_id()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id()
    logger.exception("[request_id=%s] Unhandled exception", request_id, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Window", "Retry-After"],
)


def _normalize_origin(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


_CSRF_ALLOWED_ORIGINS = {
    origin
    for origin in {
        *(_normalize_origin(origin) for origin in ALLOWED_ORIGINS),
        _normalize_origin(APP_BASE_URL),
        _normalize_origin(FRONTEND_BASE_URL),
    }
    if origin is not None
}


@app.middleware("http")
async def csrf_origin_protection_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    if method in {"GET", "HEAD", "OPTIONS"} or not path.startswith("/api/"):
        return await call_next(request)

    if path in {"/api/razorpay/webhook"}:
        return await call_next(request)

    if not IS_PROD:
        return await call_next(request)

    if not request.cookies.get("session_token"):
        return await call_next(request)

    origin = _normalize_origin(request.headers.get("origin"))
    if origin is None or origin not in _CSRF_ALLOWED_ORIGINS:
        request_id = getattr(request.state, "request_id", "-")
        return JSONResponse(
            status_code=403,
            content={
                "error": "CSRF protection blocked this request.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    return await call_next(request)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Attach security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # X-XSS-Protection is obsolete in modern browsers; setting to 0 disables
    # the broken IE/old-Chrome heuristic that could introduce vulnerabilities.
    response.headers["X-XSS-Protection"] = "0"
    if IS_PROD:
        # 2 years, include subdomains — tells browsers to always use HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    if request.cookies.get("session_token") and not request.cookies.get(CSRF_COOKIE_NAME):
        set_csrf_cookie(response, secrets.token_urlsafe(24))

    return response


rate_limiter: BaseRateLimiter = create_rate_limiter(
    max_requests=RATE_LIMIT_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    redis_url=REDIS_URL,
)


def _clear_rate_limit_state() -> None:
    rate_limiter.clear()


@app.middleware("http")
async def ip_rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client and request.client.host else "unknown"

    # Skip rate limiting for localhost in dev mode (e.g. Playwright e2e tests)
    from config import IS_PROD
    if not IS_PROD and client_ip in ("127.0.0.1", "::1", "localhost"):
        return await call_next(request)

    decision = rate_limiter.check(client_ip)
    if not decision.allowed:
        logger.warning(
            "[request_id=%s] Rate limit exceeded client_ip=%s retry_after=%ss",
            request_id,
            client_ip,
            decision.retry_after,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded. Try again shortly.",
                "request_id": request_id,
            },
            headers={
                "X-Request-ID": request_id,
                "Retry-After": str(decision.retry_after),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": str(decision.remaining),
                "X-RateLimit-Window": str(decision.window_seconds),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    response.headers["X-RateLimit-Window"] = str(decision.window_seconds)
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    return await request_context_middleware(request, call_next)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    request_id = getattr(request.state, "request_id", "-")
    logger.info(
        "[request_id=%s] %s %s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(questions.router)
app.include_router(sample.router)
app.include_router(plan.router)
app.include_router(razorpay_router.router)
app.include_router(python_questions_router.router)
app.include_router(python_data_questions_router.router)
app.include_router(pyspark_questions_router.router)
app.include_router(dashboard_router.router)
app.include_router(insights_router.router)
app.include_router(submissions_router.router)
app.include_router(mock_router.router)
app.include_router(paths_router.router)
app.include_router(spa.router)
