from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.milestone import create_milestone, delete_milestone, get_milestone, get_milestones, update_milestone
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.milestone import MilestoneCreate, MilestoneResponse, MilestoneUpdate

router = APIRouter(tags=["Milestones"])


@router.post("/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
def create(
    project_id: int,
    milestone: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return create_milestone(db, project, milestone)


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneResponse])
def read_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_milestones(db, project_id)


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update(
    milestone_id: int,
    updates: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone = get_milestone(db, milestone_id, current_user.id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return update_milestone(db, milestone, updates)


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone = get_milestone(db, milestone_id, current_user.id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    delete_milestone(db, milestone)
