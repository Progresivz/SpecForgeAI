$ErrorActionPreference = "Stop"

$ComposeFile = ".\src\docker-compose.yml"

Write-Host "=== SpecForge AI Release Validation ===" -ForegroundColor Cyan

Write-Host "`n[1/8] Running tests..."
python -m pytest .\src\tests -q

Write-Host "`n[2/8] Running production preflight..."
docker compose -f $ComposeFile exec -T app `
    sh -lc 'python scripts/production_preflight.py'

if ($LASTEXITCODE -ne 0) {
    throw "Production preflight failed."
}

Write-Host "`n[3/8] Validating nginx..."
docker compose -f $ComposeFile exec -T proxy nginx -t

if ($LASTEXITCODE -ne 0) {
    throw "nginx validation failed."
}

Write-Host "`n[4/8] Checking container health..."
docker compose -f $ComposeFile ps

$services = docker compose -f $ComposeFile ps --status running --services

if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect Compose services."
}

foreach ($required in @("db", "app", "proxy")) {
    if ($services -notcontains $required) {
        throw "Required service is not running: $required"
    }
}

Write-Host "`n[5/8] Checking HTTPS readiness..."
$response = curl.exe -k -s https://localhost/health/ready

if ($LASTEXITCODE -ne 0) {
    throw "HTTPS readiness request failed."
}

Write-Host $response

if ($response -notmatch '"ready":true') {
    throw "HTTPS readiness check failed."
}

Write-Host "`n[6/8] Finding latest valid PostgreSQL backup..."

$backup = docker compose -f $ComposeFile exec -T app `
    sh -lc 'for f in $(ls -1t /app/backups/*.dump 2>/dev/null); do if [ -s "$f" ]; then printf "%s" "$f"; exit 0; fi; done; exit 1'

if ($LASTEXITCODE -ne 0) {
    throw "Unable to find a non-empty PostgreSQL backup."
}

$backup = $backup.Trim()

if ([string]::IsNullOrWhiteSpace($backup)) {
    throw "No non-empty PostgreSQL backup was found."
}

Write-Host "Backup: $backup"

Write-Host "`n[7/8] Verifying backup restore..."

docker compose -f $ComposeFile exec -T app `
    python scripts/restore_verify.py $backup

if ($LASTEXITCODE -ne 0) {
    throw "Backup restore verification failed."
}

Write-Host "`n[8/8] Final backup inventory..."

docker compose -f $ComposeFile exec -T app `
    sh -lc 'find /app/backups -type f -name "*.dump" -size +0c -ls'

if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect backup inventory."
}

Write-Host "`n=== RELEASE VALIDATION PASSED ===" -ForegroundColor Green

