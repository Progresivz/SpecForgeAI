from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.task import create_task, delete_task, get_task, get_tasks, update_task
from app.database.deps import get_db
from app.models.user import User
from app.schemas.task import DevelopmentTaskCreate, DevelopmentTaskResponse, DevelopmentTaskUpdate, TaskPlanResponse
from app.services.task_service import auto_schedule, generate_execution_plan, task_plan

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Development Tasks"])


def _project(db, project_id, user_id):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=DevelopmentTaskResponse, status_code=status.HTTP_201_CREATED)
def create(project_id: int, payload: DevelopmentTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    try:
        return create_task(db, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[DevelopmentTaskResponse])
def list_all(project_id: int, status_filter: str | None = Query(None, alias="status"), priority: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    return get_tasks(db, project_id, status_filter, priority)


@router.get("/plan", response_model=TaskPlanResponse)
def plan(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    return task_plan(project, get_tasks(db, project_id))


@router.post("/plan/generate", response_model=list[DevelopmentTaskResponse], status_code=status.HTTP_201_CREATED)
def generate_plan(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    created = []
    try:
        for candidate in generate_execution_plan(project, get_tasks(db, project_id)):
            created.append(create_task(db, project_id, DevelopmentTaskCreate(**candidate)))
        return created
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/schedule", response_model=list[DevelopmentTaskResponse])
def schedule(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project(db, project_id, current_user.id)
    changed = auto_schedule(project, get_tasks(db, project_id))
    if changed:
        db.commit()
        for item in changed:
            db.refresh(item)
    return changed


@router.get("/{task_id}", response_model=DevelopmentTaskResponse)
def read(project_id: int, task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    item = get_task(db, task_id, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    return item


@router.put("/{task_id}", response_model=DevelopmentTaskResponse)
def update(project_id: int, task_id: int, payload: DevelopmentTaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    item = get_task(db, task_id, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        return update_task(db, item, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(project_id: int, task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project(db, project_id, current_user.id)
    item = get_task(db, task_id, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    delete_task(db, item)
