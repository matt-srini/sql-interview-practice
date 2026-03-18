import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, REDIS_URL
from database import load_datasets
from exceptions import AppError
from middleware.request_context import request_context_middleware
from middleware.request_context import get_request_id
from progress import init_progress_storage
from rate_limiter import BaseRateLimiter, create_rate_limiter
from routers import catalog, questions, sample, spa, system


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Ensure root handlers use our formatter (uvicorn may pre-configure handlers).
_root_logger = logging.getLogger()
_formatter = logging.Formatter(LOG_FORMAT)
for _handler in _root_logger.handlers:
    _handler.setFormatter(_formatter)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: load CSV datasets into DuckDB once on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_datasets()
    init_progress_storage()
    yield


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

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
    """Testing helper to clear rate-limit state where possible."""
    rate_limiter.clear()


@app.middleware("http")
async def ip_rate_limit_middleware(request: Request, call_next):
    # Keep health checks always accessible for orchestration.
    if request.url.path == "/health":
        return await call_next(request)

    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client and request.client.host else "unknown"
    decision = rate_limiter.check(client_ip)
    if not decision.allowed:
        prefix = f"[request_id={request_id}] "
        logger.warning(
            "%sRate limit exceeded client_ip=%s retry_after=%ss",
            prefix,
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
    # Register request context middleware last so it runs first.
    return await request_context_middleware(request, call_next)


# ---------------------------------------------------------------------------
# Routers — spa must be last (contains catch-all /{asset_path:path})
# ---------------------------------------------------------------------------

app.include_router(system.router)
app.include_router(catalog.router)
app.include_router(questions.router)
app.include_router(sample.router)
app.include_router(spa.router)
