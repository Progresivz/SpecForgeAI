# SpecForge AI — Phase 22

## AI-Powered Release & Quality Automation

Phase 22 adds a controlled release-automation evidence layer on top of Phase 21 release readiness.

### Capabilities
- Generate release notes from the release metadata, completed development tasks, resolved maintenance items, and recent Git commits.
- Assemble a release test suite from requirements/acceptance criteria and failed readiness gates.
- Run an optional AI senior release review using the existing OpenAI or local LLM provider.
- Produce a persisted GO / NO-GO recommendation. Deterministic release gates remain authoritative: AI cannot override a failed readiness gate.
- Preserve an evidence snapshot for each automation run.
- Expose automation history and a compact Go/No-Go endpoint.

### API
- `POST /projects/{project_id}/release/{release_id}/automation?include_ai=false`
- `GET /projects/{project_id}/release/{release_id}/automation`
- `GET /projects/{project_id}/release/{release_id}/go-no-go`

### Safety
This phase does not commit, tag, push, deploy, modify source code, or change Git history. Release promotion remains an explicit application action.

### Validation
Run `pytest` after installing `requirements.txt`.
