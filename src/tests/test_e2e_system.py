"""End-to-end SDLC validation for the complete SpecForge workflow.

The test uses a temporary SQLite database and a temporary Git repository so it
never mutates a developer's real project. It deliberately excludes AI network
calls; AI is validated separately by the existing provider/unit tests.
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("jose")
pytest.importorskip("passlib")

from fastapi.testclient import TestClient


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def test_complete_sdlc_workflow(tmp_path, monkeypatch):
    db_path = tmp_path / "e2e.db"
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "def login(email, password):\n    return True\n"
    )

    _git(repo, "init")
    _git(repo, "config", "user.email", "e2e@example.com")
    _git(repo, "config", "user.name", "E2E Tester")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial implementation")

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv(
        "SECRET_KEY",
        "e2e-secret-key-that-is-long-enough-for-tests-123456",
    )
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Pytest collection may have imported app modules before this test.
    # Reload configuration/database modules so this E2E test uses its
    # temporary DATABASE_URL and SECRET_KEY.
    import app.core.config
    import app.database.session
    import app.database.deps

    importlib.reload(app.core.config)
    importlib.reload(app.database.session)
    importlib.reload(app.database.deps)

    # Remove cached API/service modules that captured the old settings/engine.
    for module_name in list(sys.modules):
        if (
            module_name.startswith("app.api.")
            or module_name.startswith("app.services.")
        ):
            sys.modules.pop(module_name, None)

    # Import after environment setup and module isolation.
    from app.main import app

    with TestClient(app) as client:
        user = client.post(
            "/users/",
            json={
                "username": "e2e_user",
                "email": "e2e@example.com",
                "password": "StrongPass123!",
            },
        )
        assert user.status_code == 201, user.text

        login = client.post(
            "/auth/login",
            json={
                "email": "e2e@example.com",
                "password": "StrongPass123!",
            },
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        project = client.post(
            "/projects/",
            json={
                "name": "E2E Intelligence Project",
                "description": "Project used for Phase 31 intelligence validation.",
                "start_date": "2026-09-15",
                "target_date": "2026-12-31",
            },
            headers=headers,
        )
        assert project.status_code == 201, project.text

        project_id = project.json()["id"]

        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").json()["ready"] is True

        # ------------------------------------------------------------------
        # Phase 31: Requirements & Traceability Intelligence
        # ------------------------------------------------------------------

        intelligence = client.get(
            f"/projects/{project_id}/intelligence",
            headers=headers,
        )
        assert intelligence.status_code == 200, intelligence.text
        assert isinstance(intelligence.json(), dict)

        project_health = client.get(
            f"/projects/{project_id}/health",
            headers=headers,
        )
        assert project_health.status_code == 200, project_health.text
        assert isinstance(project_health.json(), dict)

        priorities = client.get(
            f"/projects/{project_id}/daily-priorities",
            headers=headers,
        )
        assert priorities.status_code == 200, priorities.text
        assert isinstance(priorities.json(), dict)

        traceability = client.get(
            f"/projects/{project_id}/intelligence/traceability-gaps",
            headers=headers,
        )
        assert traceability.status_code == 200, traceability.text

        traceability_data = traceability.json()
        assert isinstance(traceability_data, dict)

        for key in (
            "requirements",
            "trace_links",
            "requirements_with_trace",
            "requirements_with_tasks",
            "orphan_user_stories",
            "gaps",
            "coverage_percent",
        ):
            assert key in traceability_data

        # ------------------------------------------------------------------
        # Phase 31: Create controlled requirements, stories, and tasks
        # ------------------------------------------------------------------

        requirement_a = client.post(
            f"/projects/{project_id}/requirements",
            json={
                "title": "User authentication",
                "description": "The system shall allow registered users to authenticate securely.",
                "requirement_type": "functional",
                "priority": "high",
                "status": "approved",
                "rationale": "Users must be authenticated before accessing protected project data.",
                "source": "E2E Phase 31",
                "acceptance_criteria": [
                    {
                        "criterion": "Valid credentials allow the user to authenticate.",
                        "is_met": False,
                    }
                ],
            },
            headers=headers,
        )
        assert requirement_a.status_code == 201, requirement_a.text
        requirement_a_id = requirement_a.json()["id"]

        requirement_b = client.post(
            f"/projects/{project_id}/requirements",
            json={
                "title": "Project reporting",
                "description": "The system shall provide project progress reporting.",
                "requirement_type": "functional",
                "priority": "medium",
                "status": "draft",
                "rationale": "Project stakeholders need visibility into project progress.",
                "source": "E2E Phase 31",
                "acceptance_criteria": [],
            },
            headers=headers,
        )
        assert requirement_b.status_code == 201, requirement_b.text
        requirement_b_id = requirement_b.json()["id"]

        requirement_c = client.post(
            f"/projects/{project_id}/requirements",
            json={
                "title": "Audit logging",
                "description": "The system shall record security-relevant user actions.",
                "requirement_type": "functional",
                "priority": "high",
                "status": "approved",
                "rationale": "Security events must be available for audit and investigation.",
                "source": "E2E Phase 31",
                "acceptance_criteria": [
                    {
                        "criterion": "Authentication events are recorded.",
                        "is_met": False,
                    }
                ],
            },
            headers=headers,
        )
        assert requirement_c.status_code == 201, requirement_c.text
        requirement_c_id = requirement_c.json()["id"]

        story_a = client.post(
            f"/projects/{project_id}/user-stories",
            json={
                "title": "Authenticate as a registered user",
                "as_a": "registered user",
                "i_want": "to log in with my credentials",
                "so_that": "I can access protected project features",
                "priority": "high",
                "status": "draft",
            },
            headers=headers,
        )
        assert story_a.status_code == 201, story_a.text
        story_a_id = story_a.json()["id"]

        orphan_story = client.post(
            f"/projects/{project_id}/user-stories",
            json={
                "title": "View project summary",
                "as_a": "project stakeholder",
                "i_want": "to view a project summary",
                "so_that": "I can understand project progress",
                "priority": "medium",
                "status": "draft",
            },
            headers=headers,
        )
        assert orphan_story.status_code == 201, orphan_story.text
        orphan_story_id = orphan_story.json()["id"]

        # Requirement A has both a traceability link and a development task.
        task_a = client.post(
            f"/projects/{project_id}/tasks",
            json={
                "title": "Implement authentication",
                "description": "Implement the authentication flow for registered users.",
                "task_type": "development",
                "priority": "high",
                "status": "todo",
                "requirement_id": requirement_a_id,
                "user_story_id": story_a_id,
            },
            headers=headers,
        )
        assert task_a.status_code == 201, task_a.text

        trace_a = client.post(
            "/traceability",
            json={
                "requirement_id": requirement_a_id,
                "user_story_id": story_a_id,
                "coverage": "covered",
                "notes": "Requirement A is linked to its implementation story.",
            },
            headers=headers,
        )
        assert trace_a.status_code == 201, trace_a.text

        # Requirement C has a trace link but deliberately has no task.
        trace_c = client.post(
            "/traceability",
            json={
                "requirement_id": requirement_c_id,
                "user_story_id": story_a_id,
                "coverage": "covered",
                "notes": "Requirement C has a trace link but no development task.",
            },
            headers=headers,
        )
        assert trace_c.status_code == 201, trace_c.text

        # ------------------------------------------------------------------
        # Phase 31: Verify actual traceability gap detection
        # ------------------------------------------------------------------

        traceability = client.get(
            f"/projects/{project_id}/intelligence/traceability-gaps",
            headers=headers,
        )
        assert traceability.status_code == 200, traceability.text

        traceability_data = traceability.json()

        assert traceability_data["requirements"] == 3
        assert traceability_data["trace_links"] == 2
        assert traceability_data["requirements_with_trace"] == 2
        assert traceability_data["requirements_with_tasks"] == 1

        # Two requirements have no task/trace coverage respectively:
        # Requirement B has neither a trace link nor a task.
        # Requirement C has a trace link but no development task.
        gaps = traceability_data["gaps"]
        assert isinstance(gaps, list)

        gap_requirement_ids = {
            item["requirement_id"]
            for item in gaps
            if "requirement_id" in item
        }

        assert requirement_b_id in gap_requirement_ids
        assert requirement_c_id in gap_requirement_ids

        # The deliberately unlinked user story must be reported as orphaned.
        orphan_story_ids = {
            item["id"]
            for item in traceability_data["orphan_user_stories"]
            if isinstance(item, dict) and "id" in item
        }

        assert orphan_story_id in orphan_story_ids

        # Three requirements exist and two have traceability links.
        assert traceability_data["coverage_percent"] == pytest.approx(66.7, abs=0.01)

        # ------------------------------------------------------------------
        # Phase 31: Verify requirements quality intelligence
        # ------------------------------------------------------------------

        requirements_quality = client.get(
            f"/projects/{project_id}/intelligence/requirements-quality",
            headers=headers,
        )
        assert requirements_quality.status_code == 200, requirements_quality.text

        requirements_quality_data = requirements_quality.json()

        assert isinstance(requirements_quality_data, dict)

        for key in (
            "total",
            "average_score",
            "quality_band",
            "findings",
        ):
            assert key in requirements_quality_data

        assert requirements_quality_data["total"] == 3
        assert isinstance(requirements_quality_data["average_score"], (int, float))
        assert isinstance(requirements_quality_data["quality_band"], str)
        assert isinstance(requirements_quality_data["findings"], list)

        # Requirement B deliberately has no acceptance criteria.
        # The quality analyzer should therefore report a finding for it.
        requirement_b_findings = [
            item
            for item in requirements_quality_data["findings"]
            if isinstance(item, dict)
            and item.get("requirement_id") == requirement_b_id
        ]

        assert requirement_b_findings, (
            "Expected at least one quality finding for Requirement B."
        )

        finding_text = " ".join(
            str(item).lower()
            for item in requirement_b_findings
        )

        assert (
            "acceptance" in finding_text
            or "criteria" in finding_text
        ), requirement_b_findings

                # ------------------------------------------------------------------
        # Phase 31: Verify generated test-plan intelligence
        # ------------------------------------------------------------------

        test_plan = client.get(
            f"/projects/{project_id}/intelligence/test-plan",
            headers=headers,
        )
        assert test_plan.status_code == 200, test_plan.text

        test_plan_data = test_plan.json()

        assert isinstance(test_plan_data, dict)

        for key in (
            "project_id",
            "generated_on",
            "test_items",
            "coverage_percent",
        ):
            assert key in test_plan_data

        assert test_plan_data["project_id"] == project_id
        assert isinstance(test_plan_data["generated_on"], str)
        assert isinstance(test_plan_data["test_items"], list)
        assert isinstance(test_plan_data["coverage_percent"], (int, float))

        # The three controlled requirements should produce three test items.
        test_items = test_plan_data["test_items"]

        assert len(test_items) == 3

        test_requirement_ids = {
            item["requirement_id"]
            for item in test_items
            if isinstance(item, dict) and "requirement_id" in item
        }

        assert requirement_a_id in test_requirement_ids
        assert requirement_b_id in test_requirement_ids
        assert requirement_c_id in test_requirement_ids

        # The generated test plan should reflect the acceptance criteria
        # attached to Requirements A and C.
        requirement_a_tests = [
            item
            for item in test_items
            if isinstance(item, dict)
            and item.get("requirement_id") == requirement_a_id
        ]

        requirement_c_tests = [
            item
            for item in test_items
            if isinstance(item, dict)
            and item.get("requirement_id") == requirement_c_id
        ]

        assert len(requirement_a_tests) == 1
        assert len(requirement_c_tests) == 1

        assert requirement_a_tests[0]["acceptance_criteria_count"] == 1
        assert requirement_c_tests[0]["acceptance_criteria_count"] == 1

        # Requirement B deliberately has no acceptance criteria.
        requirement_b_tests = [
            item
            for item in test_items
            if isinstance(item, dict)
            and item.get("requirement_id") == requirement_b_id
        ]

        assert len(requirement_b_tests) == 1
        assert requirement_b_tests[0]["acceptance_criteria_count"] == 0

        # Test-plan coverage is based on requirements that have
        # acceptance criteria: A and C out of the three requirements.
        assert test_plan_data["coverage_percent"] == pytest.approx(
            66.7,
            abs=0.01,
        )
        # ---------------------------------------------------------
        # Phase 31 — AI-powered requirements/traceability review
        # ---------------------------------------------------------
        # Keep the E2E test deterministic and offline.
        # The live OpenAI integration is verified separately by ai_smoke.py.
        from app.services.ai_service import AIResult

        def mock_ai_review_generate(*args, **kwargs):
            return AIResult(
                provider="openai",
                model="gpt-5.6-luna",
                content=(
                    "AI review completed successfully. "
                    "Found missing acceptance criteria for Project reporting "
                    "and traceability gaps for requirements."
                ),
                knowledge_used=0,
            )
                

        monkeypatch.setattr(
            "app.api.advanced_intelligence.generate",
            mock_ai_review_generate,
        )
        def mock_requirement_improvement_generate(*args, **kwargs):
                    return AIResult(
                        provider="openai",
                        model="gpt-5.6-luna",
                        content=(
                            "Requirements improvement completed. "
                            "The requirement should use measurable language and define "
                            "explicit acceptance criteria."
                        ),
                        knowledge_used=1,
                    )

        monkeypatch.setattr(
            "app.api.advanced_intelligence.generate",
            mock_requirement_improvement_generate,
        )

        requirement_improvement_response = client.post(
            (
                f"/projects/{project_id}/intelligence/"
                f"requirements/{requirement_a_id}/improve"
            ),
            headers=headers,
        )

        assert requirement_improvement_response.status_code == 200, (
            requirement_improvement_response.text
        )

        requirement_improvement_data = requirement_improvement_response.json()

        assert isinstance(requirement_improvement_data, dict)

        for key in (
            "project_id",
            "requirement_id",
            "requirement_key",
            "provider",
            "model",
            "knowledge_used",
            "review",
        ):
            assert key in requirement_improvement_data

        assert requirement_improvement_data["project_id"] == project_id
        assert requirement_improvement_data["requirement_id"] == requirement_a_id
        assert requirement_improvement_data["requirement_key"]
        assert requirement_improvement_data["provider"] == "openai"
        assert requirement_improvement_data["model"] == "gpt-5.6-luna"
        assert requirement_improvement_data["knowledge_used"] == 1
        assert isinstance(requirement_improvement_data["review"], str)
        assert "acceptance criteria" in (
            requirement_improvement_data["review"].lower()
        )
        
        ai_review = client.post(
            f"/projects/{project_id}/intelligence/ai-review",
            headers=headers,
        )

        assert ai_review.status_code == 200, ai_review.text

        ai_review_data = ai_review.json()

        assert isinstance(ai_review_data, dict)

        for key in (
            "project_id",
            "review",
        ):
            assert key in ai_review_data

        assert ai_review_data["project_id"] == project_id
        assert isinstance(ai_review_data["review"], str)
        assert ai_review_data["review"].strip()        

        # ------------------------------------------------------------------
        # Phase 31: Verify Requirements Traceability Matrix intelligence
        # ------------------------------------------------------------------

        traceability_matrix_response = client.get(
            f"/projects/{project_id}/intelligence/traceability-matrix",
            headers=headers,
        )

        assert traceability_matrix_response.status_code == 200, (
            traceability_matrix_response.text
        )

        traceability_matrix_data = traceability_matrix_response.json()

        assert isinstance(traceability_matrix_data, dict)

        for key in (
            "project_id",
            "requirements",
            "covered_requirements",
            "coverage_percent",
            "matrix",
        ):
            assert key in traceability_matrix_data

        assert traceability_matrix_data["project_id"] == project_id
        assert traceability_matrix_data["requirements"] == 3
        assert isinstance(
            traceability_matrix_data["covered_requirements"],
            int,
        )
        assert isinstance(
            traceability_matrix_data["coverage_percent"],
            (int, float),
        )

        matrix = traceability_matrix_data["matrix"]

        assert isinstance(matrix, list)
        assert len(matrix) == 3

        matrix_by_requirement = {
            item["requirement_id"]: item
            for item in matrix
            if isinstance(item, dict)
            and "requirement_id" in item
        }

        assert requirement_a_id in matrix_by_requirement
        assert requirement_b_id in matrix_by_requirement
        assert requirement_c_id in matrix_by_requirement

        requirement_a_matrix = matrix_by_requirement[requirement_a_id]
        requirement_b_matrix = matrix_by_requirement[requirement_b_id]
        requirement_c_matrix = matrix_by_requirement[requirement_c_id]

        # Requirement A: fully connected.
        assert requirement_a_matrix["has_traceability"] is True
        assert requirement_a_matrix["has_user_story"] is True
        assert requirement_a_matrix["has_task"] is True
        assert requirement_a_matrix["has_acceptance_criteria"] is True
        assert requirement_a_matrix["acceptance_criteria_count"] == 1
        assert len(requirement_a_matrix["user_stories"]) == 1
        assert len(requirement_a_matrix["tasks"]) == 1

        # Requirement B: deliberately incomplete.
        assert requirement_b_matrix["has_traceability"] is False
        assert requirement_b_matrix["has_user_story"] is False
        assert requirement_b_matrix["has_task"] is False
        assert requirement_b_matrix["has_acceptance_criteria"] is False
        assert requirement_b_matrix["acceptance_criteria_count"] == 0

        # Requirement C: traceability exists, but implementation task
        # and acceptance criteria are intentionally missing.
        assert requirement_c_matrix["has_traceability"] is True
        assert requirement_c_matrix["has_user_story"] is True
        assert requirement_c_matrix["has_task"] is False
        assert requirement_c_matrix["has_acceptance_criteria"] is True
        assert requirement_c_matrix["acceptance_criteria_count"] == 1

        # Only Requirement A satisfies all four RTM dimensions.
        assert traceability_matrix_data["covered_requirements"] == 1
        assert traceability_matrix_data["coverage_percent"] == pytest.approx(
            33.3,
            abs=0.01,
        )