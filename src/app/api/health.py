from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine

router = APIRouter(tags=["Health"])


def _database_status() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


@router.get("/health")
def health():
    return {"status": "online", "service": settings.APP_NAME, "version": settings.VERSION}


@router.get("/health/ready")
def readiness():
    db_status = _database_status()
    ai_configured = (
        bool(settings.OPENAI_API_KEY) if settings.AI_PROVIDER.lower() == "openai"
        else bool(settings.LOCAL_LLM_URL)
    )
    ready = db_status == "ok"
    return {
        "ready": ready,
        "service": settings.APP_NAME,
        "database": db_status,
        "ai": {"provider": settings.AI_PROVIDER, "configured": ai_configured},
        "migration_mode": settings.MIGRATION_MODE,
    }
