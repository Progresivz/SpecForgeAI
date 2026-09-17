import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.database.session import SessionLocal
from app.database.init_db import create_tables
from app.observability.audit import audit_event
from app.services.backup_service import run_backup, apply_retention

logger = logging.getLogger("specforge.scheduler")
_scheduler = None


def _maintenance_job():
    """Lightweight operational job: verify DB connectivity and record an audit heartbeat."""
    db = SessionLocal()
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        audit_event("scheduled_health_check", status="ok", checked_at=datetime.now(timezone.utc).isoformat())
    except Exception:
        logger.exception("Scheduled health check failed")
        audit_event("scheduled_health_check", status="error")
    finally:
        db.close()


def _backup_job():
    db = SessionLocal()
    try:
        result = run_backup(db)
        apply_retention(db)
        audit_event("scheduled_backup", status=result.status, path=result.path, verified=result.verified)
    except Exception:
        logger.exception("Scheduled backup failed")
        audit_event("scheduled_backup", status="error")
    finally:
        db.close()

def start_scheduler(enabled: bool, interval_minutes: int = 15, backup_enabled: bool = False, backup_interval_hours: int = 24):
    global _scheduler
    if not enabled or _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
    _scheduler.add_job(_maintenance_job, "interval", minutes=max(1, interval_minutes), id="health-check", replace_existing=True)
    if backup_enabled:
        _scheduler.add_job(_backup_job, "interval", hours=max(1, backup_interval_hours), id="database-backup", replace_existing=True)
    _scheduler.start()
    logger.info("Background scheduler started interval_minutes=%s", interval_minutes)


def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Background scheduler stopped")
