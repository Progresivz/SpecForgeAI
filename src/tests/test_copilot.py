"""Integration tests for the Phase 29 AI Copilot."""
import importlib
import sys

import pytest

pytest.importorskip("jose")
pytest.importorskip("passlib")

from fastapi.testclient import TestClient


def test_copilot_chat_persistence_and_followup(tmp_path, monkeypatch):
    db_path = tmp_path / "copilot.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv(
        "SECRET_KEY",
        "copilot-test-secret-key-that-is-long-enough-123456",
    )
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Reload configuration/database modules so the test uses the
    # temporary database and test settings.
    import app.core.config
    import app.database.session

    importlib.reload(app.core.config)
    importlib.reload(app.database.session)

    # Remove cached application/API/service modules that may have
    # captured previous settings, database state, or router references.
    for module_name in list(sys.modules):
        if (
            module_name == "app.main"
            or module_name.startswith("app.api.")
            or module_name.startswith("app.services.")
        ):
            sys.modules.pop(module_name, None)

    # Re-import the application after clearing app.main so the
    # registered Copilot route references this fresh copilot module.
    from app.main import app
    import app.api.copilot as copilot_api

    def fake_generate(
        db,
        project,
        prompt,
        system_prompt,
    ):
        class FakeResult:
            content = "Mock Copilot response: project analysis completed successfully."

        return FakeResult()

    monkeypatch.setattr(copilot_api, "chat", lambda **kwargs: (
        fake_generate(
            db=kwargs["db"],
            project=kwargs["project"],
            prompt="",
            system_prompt="",
        ).content,
        {
            "project": {
                "name": kwargs["project"].name,
            },
            "health": {},
            "counts": {},
            "progress": {},
        },
        "general",
        [],
    ))

    with TestClient(app) as client:
        user = client.post(
            "/users/",
            json={
                "username": "copilot_user",
                "email": "copilot@example.com",
                "password": "StrongPass123!",
            },
        )
        assert user.status_code == 201, user.text

        login = client.post(
            "/auth/login",
            json={
                "email": "copilot@example.com",
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
                "name": "Copilot Integration Project",
                "description": "Phase 29 Copilot integration test project",
                "start_date": "2026-01-01",
                "target_date": "2026-12-31",
            },
        )
        assert project.status_code == 201, project.text

        project_id = project.json()["id"]

        # ---------------------------------------------------------
        # First Copilot message
        # ---------------------------------------------------------
        first = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Give me a general status update for this project.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert first.status_code == 200, first.text

        first_data = first.json()

        assert first_data["project_id"] == project_id
        assert first_data["message"] == (
            "Give me a general status update for this project."
        )
        assert first_data["response"] == (
            "Mock Copilot response: project analysis completed successfully."
        )
        assert first_data["mode"] == "general"
        assert isinstance(first_data["conversation_id"], int)

        conversation_id = first_data["conversation_id"]

        # ---------------------------------------------------------
        # Conversation list
        # ---------------------------------------------------------
        conversations = client.get(
            f"/projects/{project_id}/copilot/conversations",
            headers=headers,
        )

        assert conversations.status_code == 200, conversations.text

        conversation_list = conversations.json()

        assert len(conversation_list) == 1
        assert conversation_list[0]["id"] == conversation_id
        assert conversation_list[0]["project_id"] == project_id
        assert conversation_list[0]["title"] == (
            "Give me a general status update for this project."
        )
        assert conversation_list[0]["messages"] == []

        # ---------------------------------------------------------
        # Conversation detail
        # ---------------------------------------------------------
        detail = client.get(
            f"/projects/{project_id}/copilot/conversations/{conversation_id}",
            headers=headers,
        )

        assert detail.status_code == 200, detail.text

        detail_data = detail.json()

        assert detail_data["id"] == conversation_id
        assert detail_data["project_id"] == project_id
        assert len(detail_data["messages"]) == 2

        assert detail_data["messages"][0]["role"] == "user"
        assert detail_data["messages"][0]["content"] == (
            "Give me a general status update for this project."
        )

        assert detail_data["messages"][1]["role"] == "assistant"
        assert detail_data["messages"][1]["content"] == (
            "Mock Copilot response: project analysis completed successfully."
        )

        # ---------------------------------------------------------
        # Follow-up using the existing conversation
        # ---------------------------------------------------------
        followup = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "What should we prioritize next?",
                "mode": "planning",
                "include_context": True,
                "conversation_id": conversation_id,
            },
        )

        assert followup.status_code == 200, followup.text

        followup_data = followup.json()

        assert followup_data["conversation_id"] == conversation_id
        assert followup_data["project_id"] == project_id
        assert followup_data["response"] == (
            "Mock Copilot response: project analysis completed successfully."
        )

        # ---------------------------------------------------------
        # Verify persisted conversation now contains four messages
        # ---------------------------------------------------------
        final_detail = client.get(
            f"/projects/{project_id}/copilot/conversations/{conversation_id}",
            headers=headers,
        )

        assert final_detail.status_code == 200, final_detail.text

        final_messages = final_detail.json()["messages"]

        assert len(final_messages) == 4

        assert final_messages[0]["role"] == "user"
        assert final_messages[1]["role"] == "assistant"
        assert final_messages[2]["role"] == "user"
        assert final_messages[3]["role"] == "assistant"

        assert final_messages[2]["content"] == (
            "What should we prioritize next?"
        )
        assert final_messages[3]["content"] == (
            "Mock Copilot response: project analysis completed successfully."
        )
# =============================================================
# Phase 29 Copilot security and edge-case tests
# =============================================================

def _setup_copilot_test_environment(tmp_path, monkeypatch):
    """
    Create an isolated Copilot test database and reload the modules
    that depend on configuration/database settings.
    """
    db_path = tmp_path / "copilot_edge_cases.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv(
        "SECRET_KEY",
        "copilot-test-secret-key-that-is-long-enough-123456",
    )
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    import app.core.config
    import app.database.session

    importlib.reload(app.core.config)
    importlib.reload(app.database.session)

    # Remove cached application/API/service modules that may have
    # captured previous settings, database state, or router references.
    for module_name in list(sys.modules):
        if (
            module_name == "app.main"
            or module_name.startswith("app.api.")
            or module_name.startswith("app.services.")
        ):
            sys.modules.pop(module_name, None)

    # Re-import the application after clearing app.main so the
    # registered Copilot route references this fresh copilot module.
    from app.main import app
    import app.api.copilot as copilot_api

    # IMPORTANT:
    # app.main contains the FastAPI app and already-imported routers.
    # Reload it so its Copilot router is the same module that we patch.
    import app.main

    importlib.reload(app.main)

    from app.main import app
    import app.api.copilot as copilot_api

    def fake_chat(**kwargs):
        context = {
            "project": {
                "name": kwargs["project"].name,
            },
            "health": {},
            "counts": {},
            "progress": {},
        }

        return (
            "Mock Copilot response: project analysis completed successfully.",
            context if kwargs.get("include_context", True) else {},
            "general",
            [],
        )

    monkeypatch.setattr(
        copilot_api,
        "chat",
        fake_chat,
    )

    return app, copilot_api

def _create_user_and_project(client, username, email):
    """
    Create a user, log in, and create a project.
    Returns (headers, project_id).
    """
    user = client.post(
        "/users/",
        json={
            "username": username,
            "email": email,
            "password": "StrongPass123!",
        },
    )
    assert user.status_code == 201, user.text

    login = client.post(
        "/auth/login",
        json={
            "email": email,
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
            "name": f"{username} Project",
            "description": "Copilot edge-case test project",
            "start_date": "2026-01-01",
            "target_date": "2026-12-31",
        },
    )
    assert project.status_code == 201, project.text

    return headers, project.json()["id"]


def test_copilot_rejects_project_id_mismatch(tmp_path, monkeypatch):
    """
    The project_id in the request body must match the project_id
    in the URL.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
            "mismatch_user",
            "mismatch@example.com",
        )

        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id + 999,
                "message": "Test project ID mismatch.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "project_id in request body must match the URL"
        )


def test_copilot_user_cannot_access_another_users_project(
    tmp_path,
    monkeypatch,
):
    """
    A user must not be able to access another user's project.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        owner_headers, project_id = _create_user_and_project(
            client,
            "owner_user",
            "owner@example.com",
        )

        attacker_headers, _ = _create_user_and_project(
            client,
            "attacker_user",
            "attacker@example.com",
        )

        assert owner_headers != attacker_headers

        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=attacker_headers,
            json={
                "project_id": project_id,
                "message": "Try to access another user's project.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"


def test_copilot_rejects_nonexistent_conversation(
    tmp_path,
    monkeypatch,
):
    """
    A nonexistent conversation_id must return a 404 rather than
    creating or modifying a conversation.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
            "missing_conversation_user",
            "missing-conversation@example.com",
        )

        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Use a conversation that does not exist.",
                "mode": "general",
                "include_context": True,
                "conversation_id": 999999,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Copilot conversation not found"
        )


def test_copilot_rejects_foreign_conversation(
    tmp_path,
    monkeypatch,
):
    """
    A user must not be able to use a conversation owned by another
    user, even when the project itself is otherwise accessible.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        owner_headers, project_id = _create_user_and_project(
            client,
            "conversation_owner",
            "conversation-owner@example.com",
        )

        first = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=owner_headers,
            json={
                "project_id": project_id,
                "message": "Create the owner's Copilot conversation.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert first.status_code == 200, first.text

        conversation_id = first.json()["conversation_id"]

        # Create a second user. This user does not own the conversation.
        attacker_user = client.post(
            "/users/",
            json={
                "username": "conversation_attacker",
                "email": "conversation-attacker@example.com",
                "password": "StrongPass123!",
            },
        )
        assert attacker_user.status_code == 201, attacker_user.text

        attacker_login = client.post(
            "/auth/login",
            json={
                "email": "conversation-attacker@example.com",
                "password": "StrongPass123!",
            },
        )
        assert attacker_login.status_code == 200, attacker_login.text

        attacker_token = attacker_login.json()["access_token"]
        attacker_headers = {
            "Authorization": f"Bearer {attacker_token}"
        }

        # The attacker cannot even use the owner's project.
        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=attacker_headers,
            json={
                "project_id": project_id,
                "message": "Try to hijack the existing conversation.",
                "mode": "general",
                "include_context": True,
                "conversation_id": conversation_id,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"


def test_copilot_include_context_false_returns_empty_context(
    tmp_path,
    monkeypatch,
):
    """
    include_context=False must prevent project context from being
    returned in the API response.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
            "no_context_user",
            "no-context@example.com",
        )

        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Give me a response without context.",
                "mode": "general",
                "include_context": False,
            },
        )

        assert response.status_code == 200, response.text

        data = response.json()

        assert data["project_id"] == project_id
        assert data["response"] == (
            "Mock Copilot response: project analysis completed successfully."
        )
        assert data["context"] == {}


def test_copilot_chat_runtime_error_returns_503(
    tmp_path,
    monkeypatch,
):
    """
    A RuntimeError raised by the Copilot service must be converted
    into an HTTP 503 response.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    

    def failing_chat(**kwargs):
        raise RuntimeError("AI provider temporarily unavailable")

    monkeypatch.setattr(
        copilot_api,
        "chat",
        failing_chat,
    )

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
            "runtime_error_user",
            "runtime-error@example.com",
        )

        response = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Test AI failure handling.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert response.status_code == 503
        assert response.json()["detail"] == (
            "AI provider temporarily unavailable"
        )


def test_copilot_multiple_exchanges_keep_list_and_detail_consistent(
    tmp_path,
    monkeypatch,
):
    """
    After multiple exchanges, the conversation list must still contain
    the same conversation while detail contains every persisted message.
    """
    app, copilot_api = _setup_copilot_test_environment(tmp_path, monkeypatch)

    with TestClient(app) as client:
        headers, project_id = _create_user_and_project(
            client,
            "multi_exchange_user",
            "multi-exchange@example.com",
        )

        first = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "First question.",
                "mode": "general",
                "include_context": True,
            },
        )

        assert first.status_code == 200, first.text

        conversation_id = first.json()["conversation_id"]

        second = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Second question.",
                "mode": "planning",
                "include_context": True,
                "conversation_id": conversation_id,
            },
        )

        assert second.status_code == 200, second.text
        assert second.json()["conversation_id"] == conversation_id

        third = client.post(
            f"/projects/{project_id}/copilot/chat",
            headers=headers,
            json={
                "project_id": project_id,
                "message": "Third question.",
                "mode": "requirements",
                "include_context": True,
                "conversation_id": conversation_id,
            },
        )

        assert third.status_code == 200, third.text
        assert third.json()["conversation_id"] == conversation_id

        conversations = client.get(
            f"/projects/{project_id}/copilot/conversations",
            headers=headers,
        )

        assert conversations.status_code == 200, conversations.text

        conversation_list = conversations.json()

        assert len(conversation_list) == 1
        assert conversation_list[0]["id"] == conversation_id
        assert conversation_list[0]["project_id"] == project_id
        assert conversation_list[0]["messages"] == []

        detail = client.get(
            f"/projects/{project_id}/copilot/conversations/{conversation_id}",
            headers=headers,
        )

        assert detail.status_code == 200, detail.text

        detail_data = detail.json()

        assert detail_data["id"] == conversation_id
        assert detail_data["project_id"] == project_id
        assert len(detail_data["messages"]) == 6

        assert detail_data["messages"][0]["content"] == "First question."
        assert detail_data["messages"][1]["role"] == "assistant"

        assert detail_data["messages"][2]["content"] == "Second question."
        assert detail_data["messages"][3]["role"] == "assistant"

        assert detail_data["messages"][4]["content"] == "Third question."
        assert detail_data["messages"][5]["role"] == "assistant"
