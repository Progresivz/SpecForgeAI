from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.requirement import (
    add_acceptance_criterion,
    create_requirement,
    create_traceability,
    create_use_case,
    create_user_story,
    delete_requirement,
    delete_use_case,
    delete_user_story,
    get_requirement,
    get_requirements,
    get_traceability,
    get_use_case,
    get_use_cases,
    get_user_stories,
    get_user_story,
    update_requirement,
    update_use_case,
    update_user_story,
)
from app.database.deps import get_db
from app.models.user import User
from app.schemas.requirement import (
    AcceptanceCriterionCreate,
    AcceptanceCriterionResponse,
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
    SRSResponse,
    TraceabilityLinkCreate,
    TraceabilityLinkResponse,
    UseCaseCreate,
    UseCaseResponse,
    UseCaseUpdate,
    UserStoryCreate,
    UserStoryResponse,
    UserStoryUpdate,
)
from app.services.srs_service import generate_srs_markdown

router = APIRouter(tags=["Requirements"])


def _project_or_404(db, project_id, current_user):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_req(project_id: int, data: RequirementCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user)
    return create_requirement(db, project, data)


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementResponse])
def list_reqs(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    return get_requirements(db, project_id)


@router.put("/requirements/{requirement_id}", response_model=RequirementResponse)
def update_req(requirement_id: int, data: RequirementUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = get_requirement(db, requirement_id, current_user.id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return update_requirement(db, req, data)


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_req(requirement_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = get_requirement(db, requirement_id, current_user.id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    delete_requirement(db, req)


@router.post("/requirements/{requirement_id}/acceptance-criteria", response_model=AcceptanceCriterionResponse, status_code=status.HTTP_201_CREATED)
def create_criterion(requirement_id: int, data: AcceptanceCriterionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = get_requirement(db, requirement_id, current_user.id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return add_acceptance_criterion(db, req, data)


@router.post("/projects/{project_id}/user-stories", response_model=UserStoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(project_id: int, data: UserStoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user)
    return create_user_story(db, project, data)


@router.get("/projects/{project_id}/user-stories", response_model=list[UserStoryResponse])
def list_stories(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    return get_user_stories(db, project_id)


@router.put("/user-stories/{story_id}", response_model=UserStoryResponse)
def update_story(story_id: int, data: UserStoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    story = get_user_story(db, story_id, current_user.id)
    if not story:
        raise HTTPException(status_code=404, detail="User story not found")
    return update_user_story(db, story, data)


@router.delete("/user-stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(story_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    story = get_user_story(db, story_id, current_user.id)
    if not story:
        raise HTTPException(status_code=404, detail="User story not found")
    delete_user_story(db, story)


@router.post("/projects/{project_id}/use-cases", response_model=UseCaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(project_id: int, data: UseCaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user)
    return create_use_case(db, project, data)


@router.get("/projects/{project_id}/use-cases", response_model=list[UseCaseResponse])
def list_cases(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    return get_use_cases(db, project_id)


@router.put("/use-cases/{use_case_id}", response_model=UseCaseResponse)
def update_case(use_case_id: int, data: UseCaseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = get_use_case(db, use_case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=404, detail="Use case not found")
    return update_use_case(db, case, data)


@router.delete("/use-cases/{use_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(use_case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = get_use_case(db, use_case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=404, detail="Use case not found")
    delete_use_case(db, case)


@router.post("/traceability", response_model=TraceabilityLinkResponse, status_code=status.HTTP_201_CREATED)
def create_trace(data: TraceabilityLinkCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return create_traceability(db, data, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/traceability", response_model=list[TraceabilityLinkResponse])
def list_traceability(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    return get_traceability(db, project_id)


@router.get("/projects/{project_id}/srs", response_model=SRSResponse)
def get_srs(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user)
    return SRSResponse(project_id=project.id, project_name=project.name, summary_markdown=generate_srs_markdown(db, project))
