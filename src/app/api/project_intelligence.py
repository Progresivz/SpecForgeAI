from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.services.project_intelligence_service import build_intelligence, daily_priorities

router = APIRouter(prefix="/projects", tags=["Project Intelligence"])

def _project(project_id, db, user):
    project = get_project(db, project_id, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.get("/{project_id}/intelligence")
def intelligence(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_intelligence(_project(project_id, db, current_user))

@router.get("/{project_id}/health")
def health(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = build_intelligence(_project(project_id, db, current_user))
    return data["health"] | {"project_id": project_id, "risk": data["deadlines"], "maintenance": data["maintenance"]}

@router.get("/{project_id}/daily-priorities")
def priorities(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return daily_priorities(_project(project_id, db, current_user))
