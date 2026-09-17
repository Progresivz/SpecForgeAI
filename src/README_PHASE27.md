# SpecForge AI — Phase 27

## Full Production & AI Operational Validation

Phase 27 adds the final validation layer before production deployment. It does not replace deterministic release gates or bypass them.

### Added

- Non-destructive production readiness checks.
- Authenticated `GET /production/validation` endpoint.
- `scripts/production_preflight.py` for deployment preflight checks.
- `scripts/ai_smoke.py` for AI configuration validation and an optional single live AI request.
- Automated AI pipeline test with the provider call mocked, so CI does not require an API key or incur provider cost.
- Validation of database connectivity, required operational tables, backup directory writability, security configuration, AI configuration, Git availability, and PostgreSQL client availability when relevant.

## Validation commands

```powershell
python -m compileall -q app tests scripts
pytest -q
python scripts/production_preflight.py --no-tools
python scripts/ai_smoke.py
```

For a production deployment, use:

```powershell
python scripts/production_preflight.py --strict
```

For one real AI connectivity test, after configuring the provider:

```powershell
python scripts/ai_smoke.py --live
```

`--live` performs an actual model request and may incur provider usage/cost. It is intentionally not run automatically by the test suite.

## AI readiness

SpecForge supports OpenAI through the Responses API and OpenAI-compatible local endpoints. Configure `AI_PROVIDER`, the appropriate API key/URL, and model before relying on live AI generation. The default cloud model remains `gpt-5.6-luna`.

## Production definition

A successful Phase 27 validation means the software passes its automated checks and the configured infrastructure is internally consistent. It does not prove that a real cloud deployment, external PostgreSQL service, domain, TLS certificate, email service, or third-party credentials work until those are tested in the target environment.
