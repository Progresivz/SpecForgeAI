import logging
import time
import uuid
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.observability.metrics import metrics
from app.observability.scheduler import start_scheduler, stop_scheduler

from app.api.auth import router as auth_router
from app.api.ai import router as ai_router
from app.api.ai_structured import router as ai_structured_router
from app.api.copilot import router as copilot_router
from app.api.ai_tasks import router as ai_tasks_router
from app.api.dashboard import router as dashboard_router
from app.api.project_intelligence import router as project_intelligence_router
from app.api.advanced_intelligence import (
    router as advanced_intelligence_router,
    quality_router as advanced_intelligence_quality_router,
)
from app.api.code_analysis import router as code_analysis_router
from app.api.change_impact import router as change_impact_router
from app.api.workflows import router as workflows_router
from app.api.releases import router as releases_router
from app.api.release_automation import router as release_automation_router
from app.api.database_design import router as database_design_router
from app.api.documentation import router as documentation_router
from app.api.health import router as health_router
from app.api.git import router as git_router
from app.api.maintenance import router as maintenance_router
from app.api.deadlines import router as deadlines_router
from app.api.knowledge import router as knowledge_router
from app.api.tasks import router as tasks_router
from app.api.milestones import router as milestones_router
from app.api.projects import router as projects_router
from app.api.prototype import router as prototype_router
from app.api.requirements import router as requirements_router
from app.api.users import router as users_router
from app.api.observability import router as observability_router
from app.api.operations import router as operations_router
from app.api.production import router as production_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.database.init_db import create_tables
from app.database.migrations import run_migrations

configure_logging()
logger = logging.getLogger("specforge.request")
settings.validate_security()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.MIGRATION_MODE.lower() == "alembic":
        run_migrations()
    else:
        create_tables()

    start_scheduler(
        settings.ENABLE_SCHEDULER,
        settings.SCHEDULER_INTERVAL_MINUTES,
        settings.ENABLE_BACKUP_SCHEDULER,
        settings.BACKUP_INTERVAL_HOURS,
    )

    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

if settings.ENVIRONMENT.lower() in {"production", "prod"}:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_seconds = time.perf_counter() - started
        metrics.observe_request(
            request.method,
            request.url.path,
            500,
            elapsed_seconds,
        )
        logger.exception("Unhandled request error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
    elapsed_seconds = time.perf_counter() - started
    elapsed_ms = round(elapsed_seconds * 1000, 2)
    metrics.observe_request(request.method, request.url.path, response.status_code, elapsed_seconds)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    logger.info(
        "%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, elapsed_ms,
        extra={"request_id": request_id},
    )
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response




app.include_router(health_router)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(ai_structured_router)
app.include_router(copilot_router)
app.include_router(ai_tasks_router)
app.include_router(projects_router)
app.include_router(requirements_router)
app.include_router(milestones_router)
app.include_router(dashboard_router)
app.include_router(project_intelligence_router)
app.include_router(advanced_intelligence_router)
app.include_router(advanced_intelligence_quality_router)
app.include_router(code_analysis_router)
app.include_router(change_impact_router)
app.include_router(workflows_router)
app.include_router(releases_router)
app.include_router(release_automation_router)
app.include_router(database_design_router)
app.include_router(documentation_router)
app.include_router(prototype_router)
app.include_router(git_router)
app.include_router(maintenance_router)
app.include_router(deadlines_router)
app.include_router(knowledge_router)
app.include_router(tasks_router)
app.include_router(observability_router)
app.include_router(operations_router)
app.include_router(production_router)


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "static" / "index.html")
