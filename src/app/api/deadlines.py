from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.deadline import create_deadline, delete_deadline, get_deadline, get_deadlines, update_deadline
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.deadline import DeadlineCreate, DeadlineReportResponse, DeadlineResponse, DeadlineUpdate
from app.services.deadline_service import build_alerts, build_calendar, report

router = APIRouter(tags=["Deadlines"])


def _project(db, project_id, user_id):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
def create(project_id: int, data: DeadlineCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_deadline(db, _project(db, project_id, current_user.id), data)


@router.get("/projects/{project_id}/deadlines", response_model=list[DeadlineResponse])
def read_all(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    return get_deadlines(db, project_id, current_user.id)


@router.get("/projects/{project_id}/deadlines/calendar")
def calendar(project_id: int, from_date: date | None = Query(default=None), to_date: date | None = Query(default=None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    items = build_calendar(get_deadlines(db, project_id, current_user.id), date.today())
    if from_date:
        items = [i for i in items if i["due_date"] >= from_date]
    if to_date:
        items = [i for i in items if i["due_date"] <= to_date]
    return items


@router.get("/projects/{project_id}/deadlines/alerts")
def alerts(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    return build_alerts(get_deadlines(db, project_id, current_user.id), project)


@router.get("/projects/{project_id}/deadline-report", response_model=DeadlineReportResponse)
def deadline_report(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    return report(project, get_deadlines(db, project_id, current_user.id))


@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
def update(deadline_id: int, data: DeadlineUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = get_deadline(db, deadline_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return update_deadline(db, item, data)


@router.delete("/deadlines/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(deadline_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = get_deadline(db, deadline_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Deadline not found")
    delete_deadline(db, item)
