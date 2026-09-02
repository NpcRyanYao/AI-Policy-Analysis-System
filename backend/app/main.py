from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1 import api_router
from app.config import get_settings
from app.core.exceptions import AppError, error_payload
from app.core.logging import setup_logging
from app.db.session import SessionLocal, init_db
from app.services.ingest_service import ensure_seed_data
from app.workers.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging()
    init_db(settings)
    with SessionLocal() as session:
        ensure_seed_data(session, settings)
    start_scheduler(settings)
    logger.info(
        "started env=%s data_mode=%s snapshot=%s llm=%s",
        settings.app_env,
        settings.data_mode,
        settings.snapshot_id,
        settings.llm_configured,
    )
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="国内AI监管政策动态追踪与合规影响分析系统",
        description="公开政策采集 — 智能结构化解析 — 合规影响研判 — 全链路可追溯",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=error_payload(exc))

    @application.get("/")
    def root():
        return {"name": application.title, "version": __version__, "docs": "/api/docs"}

    return application


app = create_app()
