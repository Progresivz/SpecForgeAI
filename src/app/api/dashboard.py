from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.services.priority_service import calculate_priorities
from app.services.progress_service import calculate_progress
from app.services.risk_service import calculate_risk
from app.services.schedule_service import estimate_schedule

router = APIRouter(prefix="/projects", tags=["Dashboard"])


def project_for_user(project_id: int, db: Session, user: User):
    project = get_project(db, project_id, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/progress")
def progress(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return calculate_progress(project_for_user(project_id, db, current_user))


@router.get("/{project_id}/risk")
def risk(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return calculate_risk(project_for_user(project_id, db, current_user))


@router.get("/{project_id}/priorities")
def priorities(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return calculate_priorities(project_for_user(project_id, db, current_user))


@router.get("/{project_id}/summary")
def summary(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = project_for_user(project_id, db, current_user)
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "start_date": project.start_date,
            "target_date": project.target_date,
        },
        "progress": calculate_progress(project),
        "risk": calculate_risk(project),
        "schedule": estimate_schedule(project),
        "priorities": calculate_priorities(project),
    }
