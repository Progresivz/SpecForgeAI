from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.project import Project
from app.models.requirement import Requirement, UseCase, UserStory


def _bullets(items):
    return "\n".join(f"- {item}" for item in items) if items else "- None recorded."


def generate_srs_markdown(db: Session, project: Project) -> str:
    requirements = (
        db.query(Requirement)
        .options(joinedload(Requirement.acceptance_criteria))
        .filter(Requirement.project_id == project.id)
        .order_by(Requirement.requirement_type, Requirement.id)
        .all()
    )
    stories = db.query(UserStory).filter(UserStory.project_id == project.id).order_by(UserStory.id).all()
    cases = db.query(UseCase).filter(UseCase.project_id == project.id).order_by(UseCase.id).all()

    business = [r for r in requirements if r.requirement_type == "business"]
    functional = [r for r in requirements if r.requirement_type == "functional"]
    nonfunctional = [r for r in requirements if r.requirement_type == "non_functional"]
    actors = sorted({c.actor for c in cases})

    lines = [
        f"# Software Requirements Specification",
        "",
        f"**System:** {project.name}",
        f"**Generated:** {date.today().isoformat()}",
        "",
        "## 1. Introduction",
        "",
        project.description or "No project description has been provided yet.",
        "",
        "## 2. Business Requirements",
        "",
    ]
    for r in business:
        lines += [f"### {r.requirement_id} — {r.title}", r.description, f"**Priority:** {r.priority}", ""]

    lines += ["## 3. Functional Requirements", ""]
    for r in functional:
        lines += [f"### {r.requirement_id} — {r.title}", r.description, f"**Priority:** {r.priority}"]
        if r.rationale:
            lines.append(f"**Rationale:** {r.rationale}")
        if r.acceptance_criteria:
            lines += ["**Acceptance Criteria:**"] + [f"- {'[x]' if c.is_met else '[ ]'} {c.criterion}" for c in r.acceptance_criteria]
        lines.append("")

    lines += ["## 4. Non-Functional Requirements", ""]
    for r in nonfunctional:
        lines += [f"### {r.requirement_id} — {r.title}", r.description, f"**Priority:** {r.priority}", ""]

    lines += ["## 5. User Stories", ""]
    for s in stories:
        lines += [f"### {s.story_id} — {s.title}", f"As a **{s.as_a}**, I want **{s.i_want}**, so that **{s.so_that}**.", f"**Priority:** {s.priority}", ""]

    lines += ["## 6. Use Cases", ""]
    for c in cases:
        lines += [f"### {c.use_case_id} — {c.title}", f"**Actor:** {c.actor}", f"**Goal:** {c.goal}", f"**Preconditions:** {c.preconditions or 'None specified.'}", "**Main Flow:**", c.main_flow, f"**Alternate Flows:** {c.alternate_flows or 'None specified.'}", f"**Postconditions:** {c.postconditions or 'None specified.'}", ""]

    lines += ["## 7. User Interface and System Context", "", "The current requirements module records requirements, user stories, and use cases. Detailed wireframes and UI component specifications belong to the Prototype Designer module planned for a later phase.", ""]
    lines += ["## 8. Security", "", "Security requirements should be captured as non-functional requirements. No additional security controls are inferred when none have been recorded.", ""]
    lines += ["## 9. Performance", "", "Performance targets should be captured as non-functional requirements. No numeric targets are inferred when none have been recorded.", ""]
    lines += ["## 10. Maintenance", "", "Maintenance requirements and technical constraints can be added as requirements as the project evolves.", ""]
    lines += ["## 11. Stakeholders / Actors", "", _bullets(actors)]
    return "\n".join(lines)
