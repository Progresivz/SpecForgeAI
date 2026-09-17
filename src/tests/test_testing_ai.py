"""Integration tests for Phase 33 Testing AI."""

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


def _setup_app(tmp_path, monkeypatch):
    db_path = tmp_path / "phase33.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{db_path}",
    )
    monkeypatch.setenv(
        "SECRET_KEY",
        "phase33-test-secret-key-that-is-long-enough-123456",
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
            "username": "phase33_user",
            "email": "phase33@example.com",
            "password": "StrongPass123!",
        },
    )
    assert user.status_code == 201, user.text

    login = client.post(
        "/auth/login",
        json={
            "email": "phase33@example.com",
            "password": "StrongPass123!",
        },
    )
    assert login.status_code == 200, login.text

    token = login.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
    }

    project = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Phase 33 Testing AI Project",
            "description": (
                "Testing AI integration and generated-test validation."
            ),
            "start_date": "2026-01-01",
            "target_date": "2026-12-31",
        },
    )
    assert project.status_code == 201, project.text

    return headers, project.json()["id"]


def test_phase33_testing_ai(
    tmp_path,
    monkeypatch,
):
    app = _setup_app(tmp_path, monkeypatch)

    repo = tmp_path / "repo"
    repo.mkdir()

    app_file = repo / "auth.py"
    app_file.write_text(
        "def login(email, password):\n"
        "    return True\n"
    )

    _git(repo, "init")
    _git(repo, "config", "user.email", "phase33@example.com")
    _git(repo, "config", "user.name", "Phase 33 Tester")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial authentication implementation")

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(client)

        # ---------------------------------------------------------
        # Configure Git repository
        # ---------------------------------------------------------

        git = client.post(
            f"/projects/{project_id}/git/repository",
            headers=headers,
            json={
                "repo_path": str(repo),
                "default_branch": "master",
                "enabled": True,
            },
        )

        assert git.status_code == 201, git.text

        # ---------------------------------------------------------
        # Create a requirement that matches the changed source.
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
                "rationale": (
                    "Protected project access requires secure authentication."
                ),
                "source": "Phase 33 integration test",
                "acceptance_criteria": [
                    {
                        "criterion": (
                            "Valid credentials authenticate the registered user."
                        ),
                        "is_met": False,
                    },
                    {
                        "criterion": (
                            "Invalid credentials are rejected."
                        ),
                        "is_met": False,
                    },
                ],
            },
        )

        assert requirement.status_code == 201, requirement.text
        requirement_id = requirement.json()["id"]

        # ---------------------------------------------------------
        # Create a development task connected to the requirement.
        # ---------------------------------------------------------

        task = client.post(
            f"/projects/{project_id}/tasks",
            headers=headers,
            json={
                "title": "Implement authentication login",
                "description": (
                    "Implement secure login and credential validation."
                ),
                "task_type": "development",
                "priority": "high",
                "status": "todo",
                "requirement_id": requirement_id,
            },
        )

        assert task.status_code == 201, task.text

        # ---------------------------------------------------------
        # Introduce a controlled code change.
        # ---------------------------------------------------------

        app_file.write_text(
            "def login(email, password):\n"
            "    if not email or not password:\n"
            "        return False\n"
            "    # TODO: replace with real credential verification\n"
            "    return True\n"
        )

        # ---------------------------------------------------------
        # Deterministic test generation
        # ---------------------------------------------------------

        generated = client.post(
            f"/projects/{project_id}/workflows/tests",
            headers=headers,
        )

        assert generated.status_code == 200, generated.text

        generated_data = generated.json()

        assert isinstance(generated_data, list)
        assert generated_data

        generated_test = generated_data[0]

        for key in (
            "id",
            "project_id",
            "requirement_id",
            "title",
            "test_type",
            "priority",
            "steps",
            "expected_result",
            "status",
            "source",
        ):
            assert key in generated_test

        assert generated_test["project_id"] == project_id
        assert generated_test["requirement_id"] == requirement_id
        assert generated_test["status"] == "proposed"
        assert generated_test["source"] == "change_impact"
        assert generated_test["steps"]
        assert generated_test["expected_result"]

        # Authentication paths should result in a security-oriented
        # test suggestion.
        assert generated_test["test_type"] == "security"
        assert generated_test["priority"] == "high"

        # ---------------------------------------------------------
        # Persisted test retrieval
        # ---------------------------------------------------------

        listed = client.get(
            f"/projects/{project_id}/workflows/tests",
            headers=headers,
        )

        assert listed.status_code == 200, listed.text

        listed_data = listed.json()

        assert isinstance(listed_data, list)
        assert len(listed_data) >= 1

        listed_ids = {
            item["id"]
            for item in listed_data
            if isinstance(item, dict) and "id" in item
        }

        assert generated_test["id"] in listed_ids

        # ---------------------------------------------------------
        # AI-generated test
        #
        # Keep this deterministic/offline. Live OpenAI validation is
        # handled independently by ai_smoke.py.
        # ---------------------------------------------------------

        from app.services.ai_service import AIResult
        import app.api.workflows as workflows_api

        def mock_generate(*args, **kwargs):
            return AIResult(
                provider="openai",
                model="gpt-5.6-luna",
                content=(
                    "1. Submit valid authentication credentials.\n"
                    "2. Submit invalid credentials.\n"
                    "3. Submit empty credentials.\n"
                    "4. Verify protected access is denied when authentication fails.\n"
                    "Expected result: authentication behavior satisfies the "
                    "linked requirement and regression checks."
                ),
                knowledge_used=0,
            )

        monkeypatch.setattr(
            workflows_api,
            "generate",
            mock_generate,
        )

        ai_test = client.post(
            f"/projects/{project_id}/workflows/ai-tests",
            headers=headers,
        )

        assert ai_test.status_code == 200, ai_test.text

        ai_data = ai_test.json()

        assert isinstance(ai_data, dict)

        for key in (
            "id",
            "project_id",
            "title",
            "test_type",
            "priority",
            "steps",
            "expected_result",
            "status",
            "source",
        ):
            assert key in ai_data

        assert ai_data["project_id"] == project_id
        assert ai_data["title"] == "AI code-change regression test"
        assert ai_data["test_type"] == "regression"
        assert ai_data["priority"] == "high"
        assert ai_data["status"] == "proposed"
        assert ai_data["source"] == "ai"
        assert ai_data["steps"]
        assert ai_data["expected_result"]

        assert "authentication" in ai_data["steps"].lower()

        # ---------------------------------------------------------
        # Verify both deterministic and AI-generated tests persist.
        # ---------------------------------------------------------

        final_tests = client.get(
            f"/projects/{project_id}/workflows/tests",
            headers=headers,
        )

        assert final_tests.status_code == 200, final_tests.text

        final_data = final_tests.json()

        assert len(final_data) >= 2

        sources = {
            item["source"]
            for item in final_data
            if isinstance(item, dict) and "source" in item
        }

        assert "change_impact" in sources
        assert "ai" in sources

        # ---------------------------------------------------------
        # Verify workflow activity records exist.
        # ---------------------------------------------------------

        activity = client.get(
            f"/projects/{project_id}/workflows/activity",
            headers=headers,
        )

        assert activity.status_code == 200, activity.text

        activity_data = activity.json()

        assert isinstance(activity_data, list)

        actions = {
            item["action"]
            for item in activity_data
            if isinstance(item, dict) and "action" in item
        }

        assert "tests_generated" in actions
        assert "ai_test_generated" in actions
