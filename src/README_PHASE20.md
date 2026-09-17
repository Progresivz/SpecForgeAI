# SpecForge AI — Phase 20: Automated Engineering Workflows

Phase 20 turns read-only intelligence into explicit, reviewable engineering work items.

## Workflow endpoints

All endpoints require authentication and a project-owned enabled Git repository.

- `POST /projects/{project_id}/workflows/findings` — materialize current change-impact findings into a review queue.
- `GET /projects/{project_id}/workflows/findings` — review queue, optionally filtered by status.
- `PUT /projects/{project_id}/workflows/findings/{finding_id}` — accept, resolve, or dismiss a finding.
- `POST /projects/{project_id}/workflows/tasks-from-impact` — create investigation tasks from actionable impact findings.
- `POST /projects/{project_id}/workflows/tests` — generate persisted proposed regression/functional tests from change impact.
- `POST /projects/{project_id}/workflows/ai-tests` — ask the configured AI provider for an additional regression-test proposal and persist it.
- `GET /projects/{project_id}/workflows/tests` — list generated tests.
- `GET /projects/{project_id}/workflows/activity` — engineering activity/audit history.

## Safety

Workflow actions are deliberately explicit and auditable. Findings become queue records before a developer changes their status. Generated tasks and tests are proposals; SpecForge does not modify source code or Git history.
