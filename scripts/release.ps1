$ErrorActionPreference = "Stop"

Write-Host "=== SpecForge AI Release Validation ===" -ForegroundColor Cyan

Write-Host "`n[1/6] Running tests..."
python -m pytest .\src\tests -q

Write-Host "`n[2/6] Running production preflight..."
docker compose -f .\src\docker-compose.yml exec app `
    sh -lc 'python scripts/production_preflight.py'

Write-Host "`n[3/6] Validating nginx..."
docker compose -f .\src\docker-compose.yml exec proxy nginx -t

Write-Host "`n[4/6] Checking container health..."
docker compose -f .\src\docker-compose.yml ps

Write-Host "`n[5/6] Checking HTTPS readiness..."
$response = curl.exe -k -s https://localhost/health/ready
Write-Host $response

if ($response -notmatch '"ready":true') {
    throw "HTTPS readiness check failed."
}

Write-Host "`n[6/6] Checking backup storage..."
docker compose -f .\src\docker-compose.yml exec app `
    sh -lc 'find /app/backups -type f -size +0c -ls'

Write-Host "`n=== RELEASE VALIDATION PASSED ===" -ForegroundColor Green
