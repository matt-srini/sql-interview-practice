import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, IS_PROD, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, REDIS_URL
from database import close_query_engine, init_query_engine
from db import close_pool, ensure_schema, init_pool
from exceptions import AppError
from middleware.request_context import get_request_id, request_context_middleware
from rate_limiter import BaseRateLimiter, create_rate_limiter
from routers import auth, catalog, questions, sample, spa, system
from routers import plan
from routers import stripe as stripe_router
from routers import python_questions as python_questions_router
from routers import python_data_questions as python_data_questions_router
from routers import pyspark_questions as pyspark_questions_router
from routers import dashboard as dashboard_router
from routers import submissions as submissions_router
from routers import mock as mock_router
from routers import paths as paths_router


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

_root_logger = logging.getLogger()
_formatter = logging.Formatter(LOG_FORMAT)
for _handler in _root_logger.handlers:
    _handler.setFormatter(_formatter)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_query_engine()
    await init_pool()
    if not IS_PROD:
        await ensure_schema()
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
    allow_methods=["*"],
    allow_headers=["*"],
)

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


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(questions.router)
app.include_router(sample.router)
app.include_router(plan.router)
app.include_router(stripe_router.router)
app.include_router(python_questions_router.router)
app.include_router(python_data_questions_router.router)
app.include_router(pyspark_questions_router.router)
app.include_router(dashboard_router.router)
app.include_router(submissions_router.router)
app.include_router(mock_router.router)
app.include_router(paths_router.router)
app.include_router(spa.router)
