from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse, AIArtifactRequest, AIArtifactResponse
from app.services.ai_service import generate, generate_artifact

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["AI"])


def _project_or_404(db, project_id, user_id):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/generate", response_model=AIGenerateResponse)
def generate_text(project_id: int, payload: AIGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user.id)
    try:
        result = generate(db, project, payload.prompt, payload.system_prompt, payload.provider, payload.model,
                           payload.temperature, payload.max_output_tokens, payload.include_knowledge, payload.knowledge_query)
        return AIGenerateResponse(provider=result.provider, model=result.model, content=result.content, knowledge_used=result.knowledge_used)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/artifacts", response_model=AIArtifactResponse)
def generate_project_artifact(project_id: int, payload: AIArtifactRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user.id)
    try:
        result = generate_artifact(db, project, payload.artifact_type, payload.instructions,
                                   provider=payload.provider, model=payload.model,
                                   temperature=payload.temperature, max_output_tokens=payload.max_output_tokens)
        return AIArtifactResponse(project_id=project_id, artifact_type=payload.artifact_type,
                                  provider=result.provider, model=result.model, content=result.content,
                                  knowledge_used=result.knowledge_used)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

from app.crud.ai_artifact import create_artifact, get_artifact, list_artifacts
from app.schemas.ai_artifact import AIArtifactApplyRequest, AIArtifactResponse, AIArtifactUpdate
from app.services.ai_artifact_service import apply_artifact


@router.post("/artifacts/generate", response_model=AIArtifactResponse, status_code=201)
def generate_and_save_artifact(project_id: int, payload: AIArtifactRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user.id)
    try:
        result = generate_artifact(db, project, payload.artifact_type, payload.instructions,
                                   provider=payload.provider, model=payload.model,
                                   temperature=payload.temperature, max_output_tokens=payload.max_output_tokens)
        artifact = create_artifact(db, project_id, result, payload.artifact_type,
                                   f"AI {payload.artifact_type.replace('_', ' ').title()}")
        return artifact
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/artifacts/saved", response_model=list[AIArtifactResponse])
def saved_artifacts(project_id: int, artifact_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user.id)
    return list_artifacts(db, project_id, current_user.id, artifact_type)


@router.get("/artifacts/{artifact_id}", response_model=AIArtifactResponse)
def get_saved_artifact(artifact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id, current_user.id)
    if not artifact:
        raise HTTPException(status_code=404, detail="AI artifact not found")
    return artifact


@router.put("/artifacts/{artifact_id}", response_model=AIArtifactResponse)
def update_saved_artifact(artifact_id: int, payload: AIArtifactUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id, current_user.id)
    if not artifact:
        raise HTTPException(status_code=404, detail="AI artifact not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(artifact, key, value)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.delete("/artifacts/{artifact_id}", status_code=204)
def delete_saved_artifact(artifact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id, current_user.id)
    if not artifact:
        raise HTTPException(status_code=404, detail="AI artifact not found")
    db.delete(artifact)
    db.commit()


@router.post("/artifacts/{artifact_id}/apply", response_model=AIArtifactResponse)
def apply_saved_artifact(artifact_id: int, payload: AIArtifactApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id, current_user.id)
    if not artifact:
        raise HTTPException(status_code=404, detail="AI artifact not found")
    return apply_artifact(db, artifact, payload.target_type, payload.target_id, payload.title)
