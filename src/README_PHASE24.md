# SpecForge AI — Phase 24: Production Infrastructure & Deployment

Phase 24 hardens the Phase 23 application for production deployment without adding another major SDLC feature area.

## What changed

- PostgreSQL is the recommended production database.
- PostgreSQL uses `psycopg` and SQLAlchemy connection pooling/pre-ping.
- Alembic is included with an initial schema baseline.
- `MIGRATION_MODE=alembic` enables migrations at application startup.
- Production configuration rejects weak secrets, debug mode, SQLite, and non-Alembic migration mode.
- Git repository paths can be restricted with `GIT_ALLOWED_ROOTS`.
- Dockerfile includes Git because Version Control Monitor requires a Git executable.
- Docker Compose provisions PostgreSQL, the SpecForge API, and an Nginx reverse proxy.
- Persistent Docker volumes are provided for PostgreSQL, repositories, and backups.
- `/health/ready` remains the readiness endpoint and reports database/AI configuration plus migration mode.
- Request IDs, processing-time headers, security headers, and structured logging remain enabled.
- SQLite backup/restore and PostgreSQL `pg_dump`/`pg_restore` helpers were added.
- `.env.example`, `.dockerignore`, and deployment configuration are included.

## Production configuration

Copy `.env.example` to `.env` and set at minimum:

```text
POSTGRES_PASSWORD=<strong-database-password>
SECRET_KEY=<random-secret-at-least-32-characters>
OPENAI_API_KEY=<optional-if-using-cloud-AI>
```

For Docker Compose, `.env` is also used by Compose for `POSTGRES_PASSWORD` interpolation.

## Docker deployment

> Docker Desktop is required on Windows. The host does not need Python dependencies for the containerized deployment.

```powershell
copy .env.example .env
# Edit .env and set POSTGRES_PASSWORD and SECRET_KEY.
docker compose build
docker compose up -d
```

Check:

```powershell
docker compose ps
docker compose logs -f app
curl http://localhost/health/ready
```

The application container runs Alembic before serving requests. PostgreSQL data survives container recreation through `postgres_data`.

## TLS / HTTPS

The included Nginx configuration is intentionally HTTP-only so certificates are not embedded in source control. In a real deployment, terminate TLS at Nginx, a cloud load balancer, or a managed reverse proxy, then expose port 443 and provide certificates through the platform's secret/certificate mechanism.

Do not expose the application container directly to the public internet; Compose exposes it only to the internal proxy network.

## Git repositories

For production, set:

```text
GIT_ALLOWED_ROOTS=/data/repos
```

Mount project repositories beneath that directory. This prevents a project from registering an arbitrary filesystem path outside the approved repository area.

The E2E test also requires Git on the host. On Windows, verify:

```powershell
git --version
```

## Backups

SQLite:

```powershell
$env:DATABASE_URL='sqlite:///./specforge.db'
python scripts/backup_db.py
```

PostgreSQL:

```powershell
$env:DATABASE_URL='postgresql+psycopg://specforge:<password>@localhost:5432/specforge'
python scripts/backup_db.py
```

Restore a backup with:

```powershell
python scripts/restore_db.py .\backups\<backup-file>
```

For production, schedule backups externally (Windows Task Scheduler, cron, or a managed database backup service) and copy backup artifacts to durable storage. Test restores regularly.

## Windows non-Docker deployment

Create/activate a fresh virtual environment, install requirements, configure `.env`, and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:MIGRATION_MODE='create_all'  # acceptable for development/legacy SQLite
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For production Windows hosting, use PostgreSQL, `MIGRATION_MODE=alembic`, a strong `SECRET_KEY`, and a reverse proxy/service manager rather than exposing Uvicorn directly.

## Validation

Run:

```powershell
python -m compileall -q app tests scripts_e2e_smoke.py
pytest -q
python scripts_e2e_smoke.py
```

The E2E workflow requires Git. If `git --version` fails, install Git for Windows and reopen PowerShell before running the E2E test.

## Migration workflow

Development/legacy mode preserves the existing `create_all()` bootstrap and SQLite compatibility behavior.

Production should use Alembic:

```text
MIGRATION_MODE=alembic
```

Future schema changes should be added as explicit Alembic revisions. The `0001_initial` revision is a baseline for the current SQLAlchemy metadata; it is not a substitute for future granular migrations.
