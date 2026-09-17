# SpecForge AI — Phase 21

## Full SDLC Traceability & Release Management

Phase 21 connects the existing project artifacts into a release-readiness layer without replacing the earlier deterministic intelligence or AI workflows.

### SDLC traceability
`POST /projects/{project_id}/release/traceability/build` creates conservative trace links between requirements, development tasks, generated tests, database design, prototype design, and documentation. Heuristic links are marked with lower confidence and notes so they can be reviewed rather than treated as authoritative.

`GET /projects/{project_id}/release/traceability` lists persisted links.

### Release readiness
`GET /projects/{project_id}/release/readiness` evaluates gates for:
- requirements quality
- requirement → task/test coverage
- architecture health
- task completion
- test planning
- open engineering findings
- Git cleanliness/risk
- documentation presence
- critical maintenance backlog

The result contains a readiness score and individual gate evidence.

### Releases
- `POST /projects/{project_id}/release` creates a draft release.
- `GET /projects/{project_id}/release` lists releases.
- `GET /projects/{project_id}/release/{release_id}` retrieves one.
- `POST /projects/{project_id}/release/{release_id}/evaluate` refreshes readiness.
- `POST /projects/{project_id}/release/{release_id}/promote` marks a release ready only when all gates pass.

Release promotion is advisory/administrative only. It does not create Git commits, tags, pushes, deploys, or alter source code.

### Design principle
Existing Phase 17–20 analyzers remain the source of evidence. Phase 21 aggregates their outputs into persistent traceability and release gates instead of duplicating their logic.
