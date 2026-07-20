import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app import summarizer, cache
from app.routers import auth, summarize, usage, plans, webhooks, admin, url_summarize, pdf_summarize
from app.schemas import HealthResponse

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Shongkhep AI v%s ...", settings.APP_VERSION)
    init_db()
    logger.info("Database tables ready.")
    cache.connect()
    summarizer.load_model(settings.MODEL_NAME)
    yield
    logger.info("Shutting down.")
    cache.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Bangla + English article summarization — v2 with Redis, Celery & Prometheus.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.ENABLE_METRICS:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/metrics"],
        ).instrument(app).expose(app, endpoint=settings.METRICS_PATH)
        logger.info("Prometheus metrics exposed at %s", settings.METRICS_PATH)
    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed — metrics disabled.")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


API_V1 = "/api/v1"
app.include_router(auth.router,      prefix=API_V1)
app.include_router(summarize.router, prefix=API_V1)
app.include_router(usage.router,     prefix=API_V1)
app.include_router(plans.router,     prefix=API_V1)
app.include_router(webhooks.router,  prefix=API_V1)
app.include_router(admin.router,     prefix=API_V1)
app.include_router(url_summarize.router)
app.include_router(pdf_summarize.router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def health_check(request: Request):
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        model_loaded=summarizer.is_model_loaded(),
        model_info=summarizer.get_model_info(),
        redis=cache.health_check(),
        app_name=settings.APP_NAME,
    )


@app.get("/", tags=["Health"])
async def root():
    return {"message": f"{settings.APP_NAME} API v{settings.APP_VERSION}", "docs": "/docs"}
