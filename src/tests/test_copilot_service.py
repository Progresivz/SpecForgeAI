import pytest

from app.services import copilot_service


def test_detect_mode_requirements():
    result = copilot_service._detect_mode(
        "Analyze the project requirements and identify missing requirements."
    )
    assert result == "requirements"


def test_detect_mode_testing():
    result = copilot_service._detect_mode(
        "Create a testing strategy and test plan for this project."
    )
    assert result == "testing"


def test_detect_mode_deadlines():
    result = copilot_service._detect_mode(
        "What are the upcoming deadlines and schedule risks?"
    )
    assert result == "deadlines"


def test_detect_mode_general():
    result = copilot_service._detect_mode(
        "Give me a general overview of the project."
    )
    assert result == "general"


def test_build_conversation_history_limits_history():
    messages = [
        {
            "role": "user",
            "content": f"User message {index} " + ("x" * 1000),
        }
        for index in range(20)
    ]

    result = copilot_service._build_conversation_history(messages)

    assert isinstance(result, str)
    assert len(result) <= 12000


def test_build_conversation_history_preserves_recent_messages():
    class Message:
        def __init__(self, role, content):
            self.role = role
            self.content = content

    messages = [
        Message("user", f"message-{i}")
        for i in range(15)
    ]

    result = copilot_service._build_conversation_history(messages)

    assert isinstance(result, str)
    assert "message-14" in result
    assert "message-13" in result
    assert "message-4" not in result

def test_build_conversation_history_handles_empty_history():
    result = copilot_service._build_conversation_history([])

    assert isinstance(result, str)


def test_build_actions_returns_list():
    context = {
        "tasks": {
            "blocked_tasks": 0,
            "remaining": 0,
        },
        "maintenance": {
            "open": 0,
        },
        "deadlines": {
            "overdue": 0,
        },
        "requirements_coverage": {
            "coverage_percent": 100,
        },
        "health": {},
        "git": {},
    }

    result = copilot_service._build_actions(context, "general")

    assert isinstance(result, list)

def test_build_prompt_contains_user_message():
    context = {
        "project": {
            "name": "SpecForgeAI",
            "description": "AI engineering platform",
        },
        "health": {},
        "tasks": [],
        "requirements": [],
        "deadlines": [],
        "maintenance": [],
        "git": {},
    }

    prompt = copilot_service._build_prompt(
        context=context,
        message="Analyze this project.",
        mode="general",
        conversation_history="",
    )

    assert isinstance(prompt, str)
    assert "Analyze this project." in prompt
    assert "SpecForgeAI" in prompt


def test_build_prompt_contains_mode():
    context = {
        "project": {
            "name": "SpecForgeAI",
            "description": "AI engineering platform",
        },
        "health": {},
        "tasks": [],
        "requirements": [],
        "deadlines": [],
        "maintenance": [],
        "git": {},
    }

    prompt = copilot_service._build_prompt(
        context=context,
        message="Create a test plan.",
        mode="testing",
        conversation_history="",
    )

    assert isinstance(prompt, str)
    assert "testing" in prompt.lower()
