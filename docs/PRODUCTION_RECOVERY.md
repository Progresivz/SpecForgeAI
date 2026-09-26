# SpecForge AI Production Recovery Runbook

## Backup verification

List non-empty backups:

    docker compose -f .\src\docker-compose.yml exec app sh -lc 'find /app/backups -type f -size +0c -ls'

Verify a backup without modifying the live database:

    docker compose -f .\src\docker-compose.yml exec app sh -lc 'python scripts/restore_verify.py /app/backups/<BACKUP>.dump'

The restore verifier creates a temporary PostgreSQL database, restores the
backup, verifies the restored public tables, reports success, and removes the
temporary database.

## Production readiness

    curl.exe -k https://localhost/health/ready

Expected:

    "ready":true
    "database":"ok"

## Production preflight

    docker compose -f .\src\docker-compose.yml exec app sh -lc 'python scripts/production_preflight.py'

Expected:

    passed: 8
    failed: 0
    critical_failures: 0
    ready: true

## Release validation

    powershell -ExecutionPolicy Bypass -File .\scripts\release.ps1

The release gate validates tests, production configuration, nginx, container
health, HTTPS readiness, backup availability, and temporary restore recovery.

## Emergency recovery

The live database must not be overwritten during routine backup verification.

Before an emergency restore:

1. Identify a verified backup.
2. Stop application traffic as appropriate.
3. Confirm the target database and environment.
4. Preserve the existing database/volume until recovery is confirmed.
5. Restore the verified backup only after the recovery decision is approved.
6. Run production preflight.
7. Verify HTTPS readiness.
8. Review application logs.
9. Confirm application functionality.

Never use:

    docker compose down -v

as a routine recovery command.

## TLS

The current localhost certificate is self-signed for local deployment validation.

A public deployment requires a CA-issued certificate for the actual production
hostname. Private keys must remain outside Git and Docker images.
