# SpecForge AI — Phase 23

## End-to-End System Validation

Phase 23 changes the focus from adding major SDLC features to validating that the existing platform works as one integrated system.

### Validation workflow

The end-to-end test exercises:

1. User creation and authentication
2. Health/readiness
3. Project creation
4. Requirements and acceptance criteria
5. User stories and use cases
6. Explicit traceability
7. Database design and SQL export
8. Prototype design
9. Maintenance
10. Deadlines
11. Documentation generation
12. Development task planning
13. Knowledge indexing/search
14. Git repository registration/status
15. Source-code analysis
16. Real working-tree change impact
17. Engineering workflow tests/findings/activity
18. Requirements quality, architecture review, and test-plan analysis
19. Full SDLC traceability build
20. Release readiness
21. Release creation
22. Release automation
23. Final Go/No-Go decision

The test uses a temporary SQLite database and temporary Git repository. It never mutates a real project repository.

### Run validation

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the complete suite:

```powershell
pytest -q
```

Run only the full workflow:

```powershell
python scripts_e2e_smoke.py
```

AI network calls are intentionally excluded from the deterministic end-to-end test. They remain covered by the existing AI/provider tests and can be exercised separately with a configured provider.

### Phase 23 integration fix

The SQL export path now passes an explicitly requested dialect through to SQL generation instead of temporarily changing the in-memory ORM object and then reloading it. This makes `?dialect=mysql`, `?dialect=sqlite`, etc. authoritative for the returned SQL.
