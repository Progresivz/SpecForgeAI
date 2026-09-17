from __future__ import annotations

import re
from typing import Any, Sequence

from app.services.ai_service import generate
from app.services.project_intelligence_service import build_intelligence


MODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "health": (
        "health",
        "risk",
        "risks",
        "status",
        "project status",
        "overall",
        "condition",
    ),
    "requirements": (
        "requirement",
        "requirements",
        "traceability",
        "coverage",
        "acceptance criteria",
        "user story",
    ),
    "planning": (
        "plan",
        "planning",
        "roadmap",
        "next steps",
        "what should we do",
        "prioritize",
        "priority",
    ),
    "tasks": (
        "task",
        "tasks",
        "work",
        "implementation",
        "implement",
        "backlog",
    ),
    "deadlines": (
        "deadline",
        "deadlines",
        "due",
        "schedule",
        "late",
        "delay",
        "overdue",
    ),
    "maintenance": (
        "maintenance",
        "bug",
        "bugs",
        "issue",
        "issues",
        "technical debt",
        "security issue",
    ),
    "architecture": (
        "architecture",
        "design",
        "structure",
        "dependency",
        "dependencies",
        "database design",
        "api design",
    ),
    "testing": (
        "test",
        "tests",
        "testing",
        "test plan",
        "coverage",
        "quality assurance",
        "qa",
    ),
    "release": (
        "release",
        "deployment",
        "deploy",
        "version",
        "readiness",
        "production",
        "go live",
    ),
}


def _build_context(project) -> dict[str, Any]:
    intelligence = build_intelligence(project)

    return {
        "project": intelligence.get("project", {}),
        "health": intelligence.get("health", {}),
        "counts": intelligence.get("counts", {}),
        "progress": intelligence.get("progress", {}),
        "requirements_coverage": intelligence.get(
            "requirements_coverage",
            {},
        ),
        "maintenance": intelligence.get("maintenance", {}),
        "schedule": intelligence.get("schedule", {}),
        "deadlines": intelligence.get("deadlines", {}),
        "tasks": intelligence.get("tasks", {}),
        "git": intelligence.get("git", {}),
        "priorities": intelligence.get("priorities", {}),
        "recommendations": intelligence.get("recommendations", []),
    }


def _detect_mode(message: str) -> str:
    normalized = re.sub(r"\s+", " ", message.lower().strip())

    scores: dict[str, int] = {}

    for mode, keywords in MODE_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword in normalized:
                score += 1

        if score:
            scores[mode] = score

    if not scores:
        return "general"

    return max(scores, key=scores.get)


def _build_conversation_history(
    messages: Sequence[Any] | None,
    max_messages: int = 10,
    max_chars: int = 12000,
) -> str:
    """
    Convert recent Copilot messages into a bounded prompt section.

    We intentionally limit both message count and total characters so a long
    conversation cannot consume the entire AI context window.
    """
    if not messages:
        return "No previous conversation history."

    recent_messages = list(messages)[-max_messages:]

    lines: list[str] = []
    total_chars = 0

    for message in recent_messages:
        role = str(getattr(message, "role", "user")).upper()
        content = str(getattr(message, "content", "")).strip()

        if not content:
            continue

        remaining = max_chars - total_chars

        if remaining <= 0:
            break

        if len(content) > remaining:
            content = content[:remaining].rstrip() + "..."

        lines.append(f"{role}: {content}")
        total_chars += len(content)

    if not lines:
        return "No previous conversation history."

    return "\n".join(lines)


def _build_prompt(
    message: str,
    context: dict[str, Any],
    mode: str,
    conversation_history: str = "No previous conversation history.",
) -> str:
    return f"""
You are SpecForge AI Copilot, an expert software engineering assistant.

You are assisting with a real software project managed by SpecForge AI.

COPILOT MODE:
{mode}

PROJECT CONTEXT:
{context}

RECENT COPILOT CONVERSATION:
{conversation_history}

CURRENT USER REQUEST:
{message}

Core rules:

1. Use the supplied project context as the source of project facts.
2. Use recent conversation history to understand references such as
   "that task", "the previous issue", or "what I mentioned earlier".
3. Never invent project facts, metrics, requirements, deadlines, tasks,
   technologies, architecture decisions, or implementation status.
4. Clearly distinguish known facts from recommendations.
5. Give practical software-engineering guidance.
6. Prioritize risks, blocked work, deadlines, requirements coverage,
   project health, testing, maintainability, and release readiness.
7. If information is missing, explicitly identify what is missing.
8. When recommending work, explain why it matters.
9. Prefer actionable recommendations over generic advice.
10. Do not claim that an action was completed unless the supplied context
    explicitly shows that it was completed.
11. Keep the response concise enough for a project dashboard while still
    providing useful technical detail.
12. Use headings and bullet points where they improve readability.
13. Treat conversation history as conversational context, not as authoritative
    project data. Current project context takes precedence over older claims.

Mode-specific guidance:

HEALTH:
Assess project health, execution risk, schedule, deadlines, maintenance,
progress, and major delivery risks.

REQUIREMENTS:
Assess requirement completeness, coverage, traceability, acceptance criteria,
and missing requirement information.

PLANNING:
Recommend the highest-value next steps based on project state and priorities.

TASKS:
Analyze outstanding work, blocked work, task priorities, and implementation
sequence.

DEADLINES:
Analyze deadlines, schedule, remaining work, possible delays, and critical
dates.

MAINTENANCE:
Analyze open maintenance work, defects, technical debt, and security-related
maintenance concerns.

ARCHITECTURE:
Review available architectural and technical information. Do not invent
architecture that is not present in the context.

TESTING:
Assess available testing information, quality risks, test coverage, and
recommended testing work.

RELEASE:
Assess release readiness, outstanding work, risks, testing, and deployment
concerns.

GENERAL:
Provide a balanced software-engineering response using the available context.
""".strip()


def _build_actions(
    context: dict[str, Any],
    mode: str,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []

    tasks = context.get("tasks", {})
    maintenance = context.get("maintenance", {})
    deadlines = context.get("deadlines", {})
    requirements = context.get("requirements_coverage", {})
    health = context.get("health", {})
    git = context.get("git", {})

    blocked_tasks = int(tasks.get("blocked_tasks", 0) or 0)
    remaining_tasks = int(tasks.get("remaining", 0) or 0)
    open_maintenance = int(maintenance.get("open", 0) or 0)
    overdue = int(deadlines.get("overdue", 0) or 0)

    coverage = requirements.get("coverage_percent")

    if coverage is not None:
        try:
            coverage_value = float(coverage)
        except (TypeError, ValueError):
            coverage_value = 100.0
    else:
        coverage_value = 100.0

    if blocked_tasks > 0:
        actions.append(
            {
                "title": "Resolve blocked tasks",
                "reason": (
                    f"{blocked_tasks} task(s) are currently blocked and "
                    "may prevent downstream delivery."
                ),
                "priority": "critical",
                "area": "execution",
            }
        )

    if overdue > 0:
        actions.append(
            {
                "title": "Address overdue deadlines",
                "reason": (
                    f"{overdue} deadline item(s) are overdue and should be "
                    "reviewed immediately."
                ),
                "priority": "critical",
                "area": "schedule",
            }
        )

    if coverage_value < 100:
        actions.append(
            {
                "title": "Improve requirements coverage",
                "reason": (
                    f"Requirements coverage is {coverage_value:g}%. "
                    "Uncovered requirements increase delivery and "
                    "traceability risk."
                ),
                "priority": "high",
                "area": "requirements",
            }
        )

    if open_maintenance > 0:
        actions.append(
            {
                "title": "Review open maintenance work",
                "reason": (
                    f"There are {open_maintenance} open maintenance item(s) "
                    "that may affect project quality or delivery."
                ),
                "priority": "medium",
                "area": "maintenance",
            }
        )

    if remaining_tasks > 0 and mode in {
        "auto",
        "general",
        "planning",
        "tasks",
    }:
        actions.append(
            {
                "title": "Prioritize remaining implementation work",
                "reason": (
                    f"{remaining_tasks} task(s) remain. Sequence the highest-"
                    "impact work first."
                ),
                "priority": "high" if remaining_tasks >= 5 else "medium",
                "area": "planning",
            }
        )

    if git.get("available") is False:
        actions.append(
            {
                "title": "Configure project Git integration",
                "reason": (
                    "Git information is unavailable, limiting change "
                    "intelligence and source-control visibility."
                ),
                "priority": "medium",
                "area": "code intelligence",
            }
        )

    if health.get("risk", {}).get("level") == "high":
        actions.append(
            {
                "title": "Investigate high project risk",
                "reason": (
                    "The project health context reports a high-risk state."
                ),
                "priority": "critical",
                "area": "risk",
            }
        )

    return actions[:8]


def chat(
    db,
    project,
    message: str,
    mode: str = "auto",
    include_context: bool = True,
    conversation_history: Sequence[Any] | None = None,
) -> tuple[str, dict[str, Any], str, list[dict[str, str]]]:
    context = _build_context(project)

    detected_mode = (
        _detect_mode(message)
        if mode == "auto"
        else mode
    )

    prompt_context = (
        context
        if include_context
        else {
            "project": context.get("project", {}),
        }
    )

    history = _build_conversation_history(conversation_history)

    prompt = _build_prompt(
        message=message,
        context=prompt_context,
        mode=detected_mode,
        conversation_history=history,
    )

    result = generate(
        db=db,
        project=project,
        prompt=prompt,
        system_prompt=(
            "You are SpecForge AI Copilot. "
            "You provide project-aware software engineering assistance. "
            "Ground project facts in supplied context."
        ),
    )

    actions = _build_actions(context, detected_mode)

    return (
        result.content,
        context if include_context else {},
        detected_mode,
        actions,
    )
