# SpecForge AI — Phase 25

## Production Observability & Reliability

Phase 25 adds operational visibility and safer long-running deployments without changing the existing SDLC feature set.

### Added

- Prometheus-compatible HTTP metrics at `/observability/metrics` (authenticated).
- Request/error/duration instrumentation integrated with the existing request middleware.
- Structured JSON logging option with rotating file output.
- Audit-event logger for operational/background events.
- Optional APScheduler background worker with graceful startup/shutdown.
- Scheduled database health heartbeat (disabled by default).
- Backup verification utility.
- Production diagnostics utility that avoids printing secrets.
- Automated metrics test coverage.

### Configuration

```env
LOG_FORMAT=json
LOG_FILE=./logs/specforge.log
ENABLE_SCHEDULER=false
SCHEDULER_INTERVAL_MINUTES=15
```

Set `ENABLE_SCHEDULER=true` only when a single application instance is responsible for scheduled jobs. In horizontally scaled deployments, use an external scheduler/worker to avoid duplicate jobs.

### Metrics

After authentication, request:

`GET /observability/metrics`

The endpoint emits Prometheus text format. It is intentionally authenticated because request paths can reveal application structure.

### Diagnostics

```powershell
python scripts/diagnostics.py
python scripts/verify_backup.py .\backups\latest.dump
```

### Validation

Run:

```powershell
python -m compileall -q app tests scripts
pytest -q
```

For the complete workflow, keep Git installed and run:

```powershell
python scripts_e2e_smoke.py
```

Phase 25 does not claim the external Windows Git/E2E prerequisite is satisfied automatically.
