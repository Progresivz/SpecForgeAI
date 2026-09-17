$ErrorActionPreference = 'Stop'

if (-not (Test-Path '.venv')) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not $env:SECRET_KEY) {
    Write-Warning 'SECRET_KEY is not set. Use a strong secret for production.'
}

uvicorn app.main:app --host 127.0.0.1 --port 8000
