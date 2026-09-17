from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.ai_structured import StructuredAIRequest, StructuredAIResponse, StructuredApplyRequest, StructuredApplyResponse
from app.services.structured_ai_service import generate_structured, apply_structured

router = APIRouter(prefix="/projects/{project_id}/ai/structured", tags=["AI Structured"])

def _project(db, project_id, user_id):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/generate", response_model=StructuredAIResponse)
def generate(project_id: int, payload: StructuredAIRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    try:
        result, data, assumptions, count = generate_structured(
            db, project, payload.artifact_type, payload.instructions,
            provider=payload.provider, model=payload.model,
            temperature=payload.temperature, max_output_tokens=payload.max_output_tokens,
            include_knowledge=payload.include_knowledge,
        )
        return StructuredAIResponse(project_id=project_id, artifact_type=payload.artifact_type,
            provider=result.provider, model=result.model, validation_passed=True,
            item_count=count, data=data, assumptions=assumptions)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.post("/apply", response_model=StructuredApplyResponse)
def apply(project_id: int, payload: StructuredApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    try:
        created, replaced, warnings = apply_structured(db, project, payload.artifact_type, payload.data, payload.replace_existing)
        return StructuredApplyResponse(project_id=project_id, artifact_type=payload.artifact_type,
            created_count=created, replaced_existing=replaced, warnings=warnings)
    except (ValueError, TypeError, ValidationError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
