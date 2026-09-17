from __future__ import annotations

from typing import Any

from app.services.ai_service import generate
from app.services.documentation_service import (
    DOCUMENT_TYPES,
    generate_documents,
)


DOCUMENT_INSTRUCTIONS: dict[str, str] = {
    "proposal": (
        "Create a professional project proposal covering the project overview, "
        "business/technical objectives, scope, major deliverables, schedule, "
        "risks, assumptions, and success criteria."
    ),
    "srs": (
        "Create a professional Software Requirements Specification covering "
        "the project purpose, scope, functional requirements, non-functional "
        "requirements, user stories, use cases, assumptions, constraints, "
        "and acceptance considerations."
    ),
    "design": (
        "Create professional system design documentation covering architecture, "
        "major components, data flow, UI/prototype considerations, integration "
        "points, security considerations, and important design decisions."
    ),
    "database": (
        "Create professional database documentation covering the database "
        "purpose, schema, tables, columns, relationships, constraints, "
        "indexes where supported by the evidence, and data considerations."
    ),
    "api": (
        "Create professional API documentation covering API purpose, "
        "authentication, major resource areas, expected request/response "
        "behavior, and important integration considerations. Do not invent "
        "endpoints that are not supported by the supplied project evidence."
    ),
    "test_plan": (
        "Create a professional test plan covering testing scope, objectives, "
        "requirements coverage, functional testing, integration testing, "
        "security testing, regression testing, acceptance testing, risks, "
        "and recommended test cases."
    ),
    "user_manual": (
        "Create a professional user manual explaining how a user works with "
        "the project, including the major workflows and available capabilities."
    ),
    "installation": (
        "Create a professional installation and setup guide covering "
        "prerequisites, dependencies, environment configuration, database "
        "setup, application startup, and basic verification."
    ),
    "maintenance": (
        "Create a professional maintenance manual covering routine maintenance, "
        "requirements synchronization, database maintenance, documentation "
        "maintenance, monitoring considerations, troubleshooting, backups, "
        "and safe change practices."
    ),
    "release_notes": (
        "Create professional release notes based only on the supplied project "
        "evidence. Clearly identify the current state, included capabilities, "
        "important changes, known limitations, and release considerations."
    ),
    "changelog": (
        "Create a professional project changelog based only on the supplied "
        "project evidence. Do not invent historical changes that are not "
        "available in the evidence."
    ),
}


def _project_evidence(project) -> dict[str, Any]:
    requirements = list(project.requirements or [])
    stories = list(project.user_stories or [])
    use_cases = list(project.use_cases or [])

    evidence: dict[str, Any] = {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "start_date": project.start_date,
            "target_date": project.target_date,
        },
        "requirements": [
            {
                "id": getattr(item, "id", None),
                "title": getattr(item, "title", ""),
                "description": getattr(item, "description", ""),
            }
            for item in requirements
        ],
        "user_stories": [
            {
                "id": getattr(item, "story_id", None),
                "title": getattr(item, "title", ""),
                "as_a": getattr(item, "as_a", ""),
                "i_want": getattr(item, "i_want", ""),
                "so_that": getattr(item, "so_that", ""),
            }
            for item in stories
        ],
        "use_cases": [
            {
                "id": getattr(item, "use_case_id", None),
                "title": getattr(item, "title", ""),
                "actor": getattr(item, "actor", ""),
                "goal": getattr(item, "goal", ""),
            }
            for item in use_cases
        ],
    }

    design = getattr(project, "database_design", None)

    if design:
        evidence["database_design"] = {
            "name": getattr(design, "name", ""),
            "target_dialect": getattr(design, "target_dialect", ""),
            "tables": [
                {
                    "name": getattr(table, "name", ""),
                    "description": getattr(table, "description", ""),
                    "columns": [
                        {
                            "name": getattr(column, "name", ""),
                            "data_type": getattr(column, "data_type", ""),
                            "primary_key": getattr(column, "primary_key", False),
                            "nullable": getattr(column, "nullable", True),
                        }
                        for column in getattr(table, "columns", [])
                    ],
                }
                for table in getattr(design, "tables", [])
            ],
        }

    prototype = getattr(project, "prototype_design", None)

    if prototype:
        evidence["prototype"] = {
            "screens": [
                {
                    "name": getattr(screen, "name", ""),
                    "route": getattr(screen, "route", ""),
                    "purpose": getattr(screen, "purpose", ""),
                }
                for screen in getattr(prototype, "screens", [])
            ]
        }

    return evidence


def _build_prompt(project, document_type: str) -> str:
    instruction = DOCUMENT_INSTRUCTIONS[document_type]
    evidence = _project_evidence(project)

    return f"""
Create the {document_type} documentation for the following software project.

DOCUMENT REQUIREMENT:
{instruction}

PROJECT EVIDENCE:
{evidence}

Rules:
1. Use the supplied project evidence as the primary source of truth.
2. Do not invent project-specific facts, requirements, APIs, tables,
   historical changes, technologies, or capabilities.
3. When information is unavailable, explicitly state that it is not
   documented in the supplied project evidence.
4. Produce Markdown.
5. Use a clear title followed by logical Markdown headings.
6. Use tables or bullet lists where they improve clarity.
7. Make the document professional and suitable for inclusion in
   a software engineering project.
8. Keep recommendations clearly distinguishable from verified facts.
9. Do not claim that an action was performed unless the evidence shows it.
""".strip()


def generate_ai_document(
    db,
    project,
    document_type: str,
) -> dict[str, Any]:
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(
            f"Unsupported documentation type: {document_type}"
        )

    prompt = _build_prompt(project, document_type)

    result = generate(
        db,
        project,
        prompt,
        system_prompt=(
            "You are SpecForge Documentation AI. "
            "Generate accurate, professional software documentation "
            "from supplied project evidence. Never invent project facts."
        ),
    )

    baseline = {
        item["document_type"]: item
        for item in generate_documents(project, db)
    }

    generated = baseline.get(
        document_type,
        {
            "document_type": document_type,
            "title": document_type.replace("_", " ").title(),
            "content_markdown": "",
        },
    )

    return {
        "document_type": document_type,
        "title": generated["title"],
        "content_markdown": result.content,
        "provider": result.provider,
        "model": result.model,
    }