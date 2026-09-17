from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.services.advanced_intelligence_service import (
    requirement_quality,
    traceability_gaps,
    traceability_matrix,
    architecture_review,
    test_plan,
)
from app.services.ai_service import generate


router = APIRouter(
    prefix="/projects/{project_id}/intelligence",
    tags=["Advanced Intelligence"],
)


def _project(db, project_id, user):
    project = get_project(db, project_id, user.id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )
    return project


@router.get("/requirements-quality")
def requirements_quality(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return requirement_quality(_project(db, project_id, current_user))

@router.post("/requirements/{requirement_id}/improve")
def improve_requirement(
    project_id: int,
    requirement_id: int,
    instructions: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _project(db, project_id, current_user)

    requirement = next(
        (
            req
            for req in list(project.requirements or [])
            if req.id == requirement_id
        ),
        None,
    )

    if not requirement:
        raise HTTPException(
            status_code=404,
            detail="Requirement not found",
        )

    criteria = list(requirement.acceptance_criteria or [])

    requirement_context = (
        f"Requirement ID: {requirement.requirement_id}\n"
        f"Title: {requirement.title}\n"
        f"Description: {requirement.description}\n"
        f"Type: {requirement.requirement_type}\n"
        f"Priority: {requirement.priority}\n"
        f"Status: {requirement.status}\n"
        f"Rationale: {requirement.rationale or 'Not provided'}\n"
        f"Source: {requirement.source or 'Not provided'}\n"
        f"Acceptance criteria: "
        f"{[criterion.criterion for criterion in criteria] or 'None'}"
    )

    prompt = (
        "Act as a senior requirements engineer. "
        "Review the single requirement supplied below. "
        "Do not modify the requirement automatically and do not invent "
        "undocumented project facts. Identify ambiguity, missing information, "
        "testability problems, weak wording, missing rationale or source, "
        "and missing acceptance criteria. "
        "Then provide a proposed improved requirement description and "
        "proposed acceptance criteria. Clearly distinguish suggestions "
        "from documented facts.\n\n"
        f"{requirement_context}"
    )

    if instructions:
        prompt += (
            "\n\nAdditional reviewer instructions:\n"
            + instructions
        )

    try:
        result = generate(
            db,
            project,
            prompt,
            knowledge_query="requirements acceptance criteria testing",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return {
        "project_id": project_id,
        "requirement_id": requirement.id,
        "requirement_key": requirement.requirement_id,
        "provider": result.provider,
        "model": result.model,
        "knowledge_used": result.knowledge_used,
        "review": result.content,
    }


@router.get("/traceability-gaps")
def traceability(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return traceability_gaps(_project(db, project_id, current_user))


@router.get("/architecture-review")
def architecture(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return architecture_review(_project(db, project_id, current_user))


@router.get("/test-plan")
def generated_test_plan(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return test_plan(_project(db, project_id, current_user))


@router.post("/ai-review")
def ai_review(
    project_id: int,
    instructions: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _project(db, project_id, current_user)

    prompt = (
        "Act as a senior software architect and requirements reviewer. "
        "Review the project context for contradictions, ambiguous requirements, "
        "missing acceptance criteria, traceability gaps, architecture risks, "
        "testability problems, and execution risks. Return concise actionable "
        "findings grouped by severity. Do not invent facts; label assumptions explicitly."
    )

    if instructions:
        prompt += "\nAdditional reviewer instructions:\n" + instructions

    try:
        result = generate(
            db,
            project,
            prompt,
            knowledge_query="architecture requirements testing",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return {
        "project_id": project_id,
        "provider": result.provider,
        "model": result.model,
        "review": result.content,
    }


# Compatibility alias:
# The E2E/API contract expects /projects/{project_id}/requirements-quality
# while the original advanced-intelligence namespace remains available.
quality_router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["Advanced Intelligence"],
)


@quality_router.get("/requirements-quality")
def requirements_quality_compat(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return requirement_quality(_project(db, project_id, current_user))

@quality_router.get("/architecture-review")
def architecture_review_compat(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return architecture_review(_project(db, project_id, current_user))


@quality_router.get("/traceability-gaps")
def traceability_gaps_compat(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return traceability_gaps(_project(db, project_id, current_user))

@router.get("/traceability-matrix")
def traceability_matrix_view(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return traceability_matrix(_project(db, project_id, current_user))


@quality_router.get("/test-plan")
def test_plan_compat(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return test_plan(_project(db, project_id, current_user))