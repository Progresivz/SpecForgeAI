"""Integration tests for Phase 32 Code & Change Intelligence."""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("jose")
pytest.importorskip("passlib")

from fastapi.testclient import TestClient


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=cwd,
        text=True,
    ).strip()


def _setup_environment(tmp_path, monkeypatch):
    db_path = tmp_path / "code_intelligence.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv(
        "SECRET_KEY",
        "phase32-test-secret-key-that-is-long-enough-123456",
    )
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    import app.core.config
    import app.database.session

    importlib.reload(app.core.config)
    importlib.reload(app.database.session)

    for module_name in list(sys.modules):
        if (
            module_name.startswith("app.api.")
            or module_name.startswith("app.services.")
        ):
            sys.modules.pop(module_name, None)

    import app.main

    importlib.reload(app.main)

    return app.main.app


def _create_user_and_project(client):
    user = client.post(
        "/users/",
        json={
            "username": "phase32_user",
            "email": "phase32@example.com",
            "password": "StrongPass123!",
        },
    )
    assert user.status_code == 201, user.text

    login = client.post(
        "/auth/login",
        json={
            "email": "phase32@example.com",
            "password": "StrongPass123!",
        },
    )
    assert login.status_code == 200, login.text

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Phase 32 Code Intelligence Project",
            "description": "Code and change intelligence integration test.",
            "start_date": "2026-01-01",
            "target_date": "2026-12-31",
        },
    )
    assert project.status_code == 201, project.text

    return headers, project.json()["id"]


def _configure_repository(client, headers, project_id, repo):
    response = client.post(
        f"/projects/{project_id}/git/repository",
        headers=headers,
        json={
            "repo_path": str(repo),
            "branch": "master",
            "enabled": True,
        },
    )

    if response.status_code == 404:
        response = client.post(
            f"/projects/{project_id}/git",
            headers=headers,
            json={
                "repo_path": str(repo),
                "branch": "master",
                "enabled": True,
            },
        )

    assert response.status_code in (200, 201), response.text


def test_phase32_code_and_change_intelligence(
    tmp_path,
    monkeypatch,
):
    app = _setup_environment(tmp_path, monkeypatch)

    repo = tmp_path / "repo"
    repo.mkdir()

    app_file = repo / "app.py"
    app_file.write_text(
        "def login(email, password):\n"
        "    return True\n"
    )

    _git(repo, "init")
    _git(repo, "config", "user.email", "phase32@example.com")
    _git(repo, "config", "user.name", "Phase 32 Tester")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial implementation")

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
        )

        _configure_repository(
            client,
            headers,
            project_id,
            repo,
        )

        # ---------------------------------------------------------
        # Create controlled requirement and task
        # ---------------------------------------------------------

        requirement = client.post(
            f"/projects/{project_id}/requirements",
            headers=headers,
            json={
                "title": "User authentication",
                "description": (
                    "The system shall allow registered users to "
                    "authenticate securely."
                ),
                "requirement_type": "functional",
                "priority": "high",
                "status": "approved",
                "rationale": "Protected project access requires authentication.",
                "source": "Phase 32 test",
                "acceptance_criteria": [
                    {
                        "criterion": (
                            "Valid credentials allow the user to authenticate."
                        ),
                        "is_met": False,
                    }
                ],
            },
        )
        assert requirement.status_code == 201, requirement.text
        requirement_id = requirement.json()["id"]

        task = client.post(
            f"/projects/{project_id}/tasks",
            headers=headers,
            json={
                "title": "Implement authentication login",
                "description": (
                    "Implement secure user authentication and login."
                ),
                "task_type": "development",
                "priority": "high",
                "status": "todo",
                "requirement_id": requirement_id,
            },
        )
        assert task.status_code == 201, task.text

        # ---------------------------------------------------------
        # Code analysis
        # ---------------------------------------------------------

        analysis = client.get(
            f"/projects/{project_id}/code/analysis",
            headers=headers,
        )

        assert analysis.status_code == 200, analysis.text

        analysis_data = analysis.json()

        assert isinstance(analysis_data, dict)
        assert analysis_data["files_analyzed"] >= 1
        assert isinstance(analysis_data["files"], list)
        assert isinstance(analysis_data["findings"], list)
        assert "finding_counts" in analysis_data

        analyzed_paths = {
            item["path"]
            for item in analysis_data["files"]
            if isinstance(item, dict)
        }

        assert "app.py" in analyzed_paths

        # ---------------------------------------------------------
        # Code file listing
        # ---------------------------------------------------------

        files_response = client.get(
            f"/projects/{project_id}/code/files",
            headers=headers,
        )

        assert files_response.status_code == 200, files_response.text

        files_data = files_response.json()

        assert isinstance(files_data, dict)
        assert "files" in files_data
        assert files_data["files_analyzed"] >= 1

        # ---------------------------------------------------------
        # Modify repository so Git change intelligence has
        # a deterministic changed file.
        # ---------------------------------------------------------

        app_file.write_text(
            "def login(email, password):\n"
            "    # TODO: add real authentication validation\n"
            "    return True\n"
        )

        # ---------------------------------------------------------
        # Changed-code review
        # ---------------------------------------------------------

        changed_review = client.get(
            f"/projects/{project_id}/code/changes/review",
            headers=headers,
        )

        assert changed_review.status_code == 200, changed_review.text

        changed_data = changed_review.json()

        assert isinstance(changed_data, dict)
        assert changed_data["code_files_changed"] >= 1
        assert isinstance(changed_data["changed_files"], list)
        assert isinstance(changed_data["findings"], list)

        changed_paths = {
            item["path"]
            for item in changed_data["changed_files"]
            if isinstance(item, dict) and "path" in item
        }

        assert "app.py" in changed_paths

        # ---------------------------------------------------------
        # Git diff context
        # ---------------------------------------------------------

        diff_response = client.get(
            f"/projects/{project_id}/code/changes/diff",
            headers=headers,
        )

        assert diff_response.status_code == 200, diff_response.text

        diff_data = diff_response.json()

        assert isinstance(diff_data, dict)
        assert diff_data["base"] == "HEAD"
        assert isinstance(diff_data["diff"], str)
        assert diff_data["diff"]
        assert "impact" in diff_data
        assert "app.py" in diff_data["diff"]

        # ---------------------------------------------------------
        # Change impact
        # ---------------------------------------------------------

        impact_response = client.get(
            f"/projects/{project_id}/code/changes/impact",
            headers=headers,
        )

        assert impact_response.status_code == 200, impact_response.text

        impact_data = impact_response.json()

        assert isinstance(impact_data, dict)
        assert impact_data["code_files_changed"] >= 1
        assert isinstance(impact_data["changed_files"], list)
        assert isinstance(impact_data["affected"], dict)
        assert "requirements" in impact_data["affected"]
        assert "tasks" in impact_data["affected"]
        assert isinstance(impact_data["findings"], list)
        assert isinstance(impact_data["test_suggestions"], list)

        # ---------------------------------------------------------
        # AI code review
        #
        # Keep this deterministic and offline. Live AI is tested
        # separately by ai_smoke.py.
        # ---------------------------------------------------------

        from app.services.ai_service import AIResult
        import app.api.change_impact as change_impact_api

        def mock_generate(*args, **kwargs):
            return AIResult(
                provider="openai",
                model="gpt-5.6-luna",
                content=(
                    "Code change review completed successfully. "
                    "The authentication change should include regression "
                    "tests and verify secure credential handling."
                ),
                knowledge_used=0,
            )

        monkeypatch.setattr(
            change_impact_api,
            "generate",
            mock_generate,
        )

        ai_review = client.post(
            f"/projects/{project_id}/code/changes/ai-review",
            headers=headers,
        )

        assert ai_review.status_code == 200, ai_review.text

        ai_data = ai_review.json()

        assert isinstance(ai_data, dict)
        assert ai_data["project_id"] == project_id
        assert ai_data["base"] == "HEAD"
        assert ai_data["provider"] == "openai"
        assert ai_data["model"] == "gpt-5.6-luna"
        assert isinstance(ai_data["review"], str)
        assert ai_data["review"].strip()
        assert isinstance(ai_data["impact"], dict)
        assert isinstance(ai_data["diff_truncated"], bool)
