from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.ai_structured import StructuredAIRequest, StructuredAIResponse
from app.services.structured_ai_service import generate_structured

router = APIRouter(prefix="/projects/{project_id}/ai/tasks", tags=["AI Development Tasks"])

@router.post("/generate", response_model=StructuredAIResponse)
def generate_tasks(project_id: int, payload: StructuredAIRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        result, data, assumptions, count = generate_structured(
            db, project, "development_tasks", payload.instructions,
            provider=payload.provider, model=payload.model,
            temperature=payload.temperature, max_output_tokens=payload.max_output_tokens,
            include_knowledge=payload.include_knowledge,
        )
        return StructuredAIResponse(project_id=project_id, artifact_type="development_tasks",
            provider=result.provider, model=result.model, validation_passed=True,
            item_count=count, data=data, assumptions=assumptions)
    except (ValueError, TypeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
