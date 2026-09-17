import json
from typing import Type
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.ai_structured import (
    DatabaseInput, MaintenanceInput, PrototypeInput, RequirementInput,
    StructuredType, UserStoryInput,
)
from app.services.ai_service import generate
from app.crud.requirement import create_requirement, create_user_story
from app.crud.database_design import create_or_replace_design
from app.crud.prototype import create_or_replace_design as create_prototype
from app.crud.maintenance import create_item
from app.schemas.requirement import RequirementCreate, UserStoryCreate
from app.schemas.database_design import DatabaseDesignCreate, DatabaseTableCreate, DatabaseColumnCreate, DatabaseRelationshipCreate
from app.schemas.prototype import PrototypeDesignCreate, PrototypeScreenCreate, PrototypeComponentCreate, PrototypeFlowCreate
from app.schemas.maintenance import MaintenanceItemCreate
from app.schemas.task import DevelopmentTaskCreate
from app.crud.task import create_task

MODEL_MAP: dict[str, tuple[Type[BaseModel], str]] = {
    "requirements": (RequirementInput, "requirements"),
    "user_stories": (UserStoryInput, "user_stories"),
    "database": (DatabaseInput, "database"),
    "prototype": (PrototypeInput, "prototype"),
    "maintenance": (MaintenanceInput, "maintenance"),
    "development_tasks": (DevelopmentTaskCreate, "development_tasks"),
}

PROMPTS = {
    "requirements": "Return a JSON object {\"items\": [...], \"assumptions\": [...]} containing implementation-ready requirements. Each item must include title, description, requirement_type, priority, status, rationale, source, and acceptance_criteria[].",
    "user_stories": "Return a JSON object {\"items\": [...], \"assumptions\": [...]} containing implementation-ready user stories. Each item must include title, as_a, i_want, so_that, priority, status.",
    "database": "Return a JSON object {\"design\": {...}, \"assumptions\": [...]} matching the supplied database schema. Do not invent entities unsupported by context unless explicitly marked as an assumption.",
    "prototype": "Return a JSON object {\"design\": {...}, \"assumptions\": [...]} matching the supplied prototype schema. Keep screens and flows consistent with known requirements.",
    "maintenance": "Return a JSON object {\"items\": [...], \"assumptions\": [...]} containing actionable maintenance items supported by the project context.",
    "development_tasks": "Return a JSON object {\"items\": [...], \"assumptions\": [...]} containing implementation-ready development tasks. Prefer tasks that trace to requirements, user stories, milestones, or maintenance items. Include estimates and dependencies when supported by context.",
}


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("AI response did not contain a JSON object")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("AI response must be a JSON object")
    return value


def _normalize_payload(artifact_type: str, raw: dict) -> dict:
    if artifact_type in {"requirements", "user_stories", "maintenance", "development_tasks"}:
        if not isinstance(raw.get("items"), list):
            raise ValueError("Structured response must contain an items array")
        return {"items": raw["items"], "assumptions": raw.get("assumptions", [])}
    if not isinstance(raw.get("design"), dict):
        raise ValueError("Structured response must contain a design object")
    return {"design": raw["design"], "assumptions": raw.get("assumptions", [])}


def generate_structured(db: Session, project: Project, artifact_type: str, instructions: str | None = None, **kwargs):
    if artifact_type not in MODEL_MAP:
        raise ValueError(f"Unsupported structured artifact type: {artifact_type}")
    prompt = PROMPTS[artifact_type]
    if instructions:
        prompt += "\nAdditional instructions:\n" + instructions
    prompt += "\nReturn JSON only. No Markdown fences. Use null for unknown optional values. Do not add fields outside the schema."
    result = generate(db, project, prompt, knowledge_query=artifact_type, **kwargs)
    raw = _normalize_payload(artifact_type, _extract_json(result.content))
    schema, _ = MODEL_MAP[artifact_type]
    if artifact_type in {"requirements", "user_stories", "maintenance", "development_tasks"}:
        validated = [schema.model_validate(x) for x in raw["items"]]
        data = {"items": [x.model_dump(mode="json") for x in validated]}
        count = len(validated)
    else:
        validated = schema.model_validate(raw["design"])
        data = {"design": validated.model_dump(mode="json")}
        count = len(getattr(validated, "tables", []) or getattr(validated, "screens", []) or [])
    return result, data, raw.get("assumptions", []), count


def apply_structured(db: Session, project: Project, artifact_type: str, data: dict, replace_existing: bool = False):
    warnings = []
    if artifact_type == "requirements":
        items = [RequirementInput.model_validate(x) for x in data.get("items", [])]
        created = 0
        for item in items:
            create_requirement(db, project, RequirementCreate(**item.model_dump()))
            created += 1
        return created, False, warnings
    if artifact_type == "user_stories":
        items = [UserStoryInput.model_validate(x) for x in data.get("items", [])]
        created = 0
        for item in items:
            create_user_story(db, project, UserStoryCreate(**item.model_dump()))
            created += 1
        return created, False, warnings
    if artifact_type == "maintenance":
        items = [MaintenanceInput.model_validate(x) for x in data.get("items", [])]
        created = 0
        for item in items:
            create_item(db, project.id, MaintenanceItemCreate(**item.model_dump()))
            created += 1
        return created, False, warnings
    if artifact_type == "development_tasks":
        items = [DevelopmentTaskCreate.model_validate(x) for x in data.get("items", [])]
        created = 0
        for item in items:
            create_task(db, project.id, DevelopmentTaskCreate(**item.model_dump()))
            created += 1
        return created, False, warnings
    if artifact_type == "database":
        design = DatabaseInput.model_validate(data["design"])
        if not replace_existing and project.database_design:
            warnings.append("Existing database design retained; use replace_existing=true to replace it.")
            return 0, False, warnings
        payload = DatabaseDesignCreate(
            name=design.name, target_dialect=design.target_dialect, notes=design.notes,
            tables=[DatabaseTableCreate(name=t.name, description=t.description, columns=[DatabaseColumnCreate(**c.model_dump()) for c in t.columns]) for t in design.tables],
            relationships=[DatabaseRelationshipCreate(**r.model_dump()) for r in design.relationships],
        )
        create_or_replace_design(db, project, payload)
        return len(design.tables), replace_existing and bool(project.database_design), warnings
    if artifact_type == "prototype":
        design = PrototypeInput.model_validate(data["design"])
        if not replace_existing and project.prototype_design:
            warnings.append("Existing prototype design retained; use replace_existing=true to replace it.")
            return 0, False, warnings
        payload = PrototypeDesignCreate(
            name=design.name, description=design.description, style_notes=design.style_notes,
            screens=[PrototypeScreenCreate(name=s.name, route=s.route, purpose=s.purpose, layout=s.layout,
                     components=[PrototypeComponentCreate(**c.model_dump()) for c in s.components]) for s in design.screens],
            flows=[PrototypeFlowCreate(**f.model_dump()) for f in design.flows],
        )
        create_prototype(db, project, payload)
        return len(design.screens), replace_existing and bool(project.prototype_design), warnings
    raise ValueError(f"Unsupported structured artifact type: {artifact_type}")
