# SpecForge AI — Phase 26

## Operational Automation & Backup Management

Phase 26 adds database backup execution, verification, retention, backup history, operational job history, and optional scheduled backups.

### Endpoints
- `POST /operations/backups`
- `GET /operations/backups`
- `POST /operations/backups/retention`
- `POST /operations/backups/{backup_id}/verify`
- `GET /operations/status`
- `GET /operations/jobs`

All operational endpoints require authentication.

### Configuration
`BACKUP_DIR`, `BACKUP_RETENTION_DAYS`, `BACKUP_RETENTION_COUNT`, `ENABLE_BACKUP_SCHEDULER`, and `BACKUP_INTERVAL_HOURS` are available in `.env`.

Backups use SQLite's online backup API for SQLite and `pg_dump --format=custom` for PostgreSQL. Verification uses SQLite `PRAGMA integrity_check` or `pg_restore --list` for PostgreSQL.

Scheduled backups remain disabled by default. In a multi-instance deployment, enable the scheduler on only one instance or move scheduling to an external worker.
