from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    critical: bool = False

    def as_dict(self):
        return asdict(self)


def _check(name, fn, critical=False):
    try:
        ok, message = fn()
        return CheckResult(name, "pass" if ok else "fail", message, critical)
    except Exception as exc:
        return CheckResult(name, "fail", str(exc), critical)


def validate_environment(include_tools: bool = True) -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.append(_check(
        "configuration.security",
        lambda: (
            (
                not settings.ENVIRONMENT.lower() in {"production", "prod"}
                or (
                    settings.MIGRATION_MODE.lower() == "alembic"
                    and not settings.DEBUG
                    and len(settings.SECRET_KEY) >= 32
                    and settings.SECRET_KEY != "dev-only-change-this-secret-key"
                    and not settings.DATABASE_URL.lower().startswith("sqlite")
                    and bool(settings.cors_origins)
                    and all(origin.startswith("https://") for origin in settings.cors_origins)
                    and (settings.AI_PROVIDER.lower() != "openai" or bool(settings.OPENAI_API_KEY.strip()))
                    and bool(settings.git_allowed_roots)
                )
            ),
            "production security configuration is valid"
            if settings.ENVIRONMENT.lower() in {"production", "prod"}
            else "development configuration accepted",
        ),
        critical=True,
    ))
    checks.append(_check(
        "database.connection",
        lambda: _database_check(),
        critical=True,
    ))
    checks.append(_check(
        "database.tables",
        lambda: _tables_check(),
        critical=True,
    ))
    checks.append(_check(
        "backup.directory",
        lambda: _backup_check(),
        critical=True,
    ))
    checks.append(_check(
        "ai.configuration",
        lambda: _ai_config_check(),
        critical=False,
    ))
    if include_tools:
        for tool in ("git", "pg_dump", "pg_restore"):
            checks.append(_check(
                f"tool.{tool}",
                lambda tool=tool: _tool_check(tool),
                critical=(tool == "git"),
            ))
    return checks


def _database_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True, f"database reachable ({engine.url.get_backend_name()})"


def _tables_check():
    required = {"users", "projects", "requirements", "operational_jobs", "backup_records"}
    from sqlalchemy import inspect
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
    missing = sorted(required - tables)
    return (not missing, "required tables present" if not missing else f"missing tables: {', '.join(missing)}")


def _backup_check():
    path = Path(settings.BACKUP_DIR).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write-test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)
    return True, f"backup directory writable: {path.resolve()}"


def _ai_config_check():
    provider = settings.AI_PROVIDER.lower()
    if provider == "openai":
        return bool(settings.OPENAI_API_KEY), "OpenAI API key configured" if settings.OPENAI_API_KEY else "OPENAI_API_KEY is not configured"
    if provider == "local":
        return bool(settings.LOCAL_LLM_URL), "local LLM endpoint configured" if settings.LOCAL_LLM_URL else "LOCAL_LLM_URL is not configured"
    return False, f"unsupported AI provider: {settings.AI_PROVIDER}"


def _tool_check(tool):
    path = shutil.which(tool)
    if path:
        return True, path
    # pg tools are not required for SQLite deployments.
    if tool in {"pg_dump", "pg_restore"} and engine.url.get_backend_name() != "postgresql":
        return True, "not required for current database backend"
    return False, f"{tool} was not found on PATH"


def summarize(checks: list[CheckResult]) -> dict:
    failed_critical = [c for c in checks if c.status == "fail" and c.critical]
    failed = [c for c in checks if c.status == "fail"]
    return {
        "passed": len([c for c in checks if c.status == "pass"]),
        "failed": len(failed),
        "critical_failures": len(failed_critical),
        "ready": not failed_critical,
        "checks": [c.as_dict() for c in checks],
    }
