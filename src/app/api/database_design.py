from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.database_design import create_or_replace_design, delete_design, get_design
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.database_design import DatabaseDesignCreate, DatabaseDesignResponse, SQLExportResponse
from app.services.database_service import generate_sql

router = APIRouter(tags=["Database Designer"])


def _project_or_404(db, project_id, current_user):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/database-design", response_model=DatabaseDesignResponse, status_code=status.HTTP_201_CREATED)
def save_database_design(project_id: int, data: DatabaseDesignCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id, current_user)
    try:
        return create_or_replace_design(db, project, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/database-design", response_model=DatabaseDesignResponse)
def get_database_design(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    design = get_design(db, project_id, current_user.id)
    if not design:
        raise HTTPException(status_code=404, detail="Database design not found")
    return design


@router.delete("/projects/{project_id}/database-design", status_code=status.HTTP_204_NO_CONTENT)
def remove_database_design(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    design = get_design(db, project_id, current_user.id)
    if not design:
        raise HTTPException(status_code=404, detail="Database design not found")
    delete_design(db, design)


@router.get("/projects/{project_id}/database-design/sql", response_model=SQLExportResponse)
def export_database_sql(project_id: int, dialect: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_or_404(db, project_id, current_user)
    design = get_design(db, project_id, current_user.id)
    if not design:
        raise HTTPException(status_code=404, detail="Database design not found")
    if dialect:
        dialect = dialect.lower()
        if dialect not in {"postgresql", "mysql", "sqlite", "sqlserver"}:
            raise HTTPException(status_code=400, detail="dialect must be postgresql, mysql, sqlite, or sqlserver")
        design.target_dialect = dialect
    return SQLExportResponse(project_id=project_id, dialect=design.target_dialect, sql=generate_sql(db, design, dialect=dialect))
