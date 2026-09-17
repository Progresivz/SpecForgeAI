from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.git_repository import get_repository
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.services import code_analysis_service
from app.services.git_service import GitError

router = APIRouter(tags=['Code-Aware Engineering AI'])


def _context(project_id: int, db: Session, user: User):
    project = get_project(db, project_id, user.id)
    if not project:
        raise HTTPException(404, 'Project not found')
    repo = get_repository(db, project_id, user.id)
    if not repo or not repo.enabled:
        raise HTTPException(409, 'Git repository is not configured or is disabled')
    return project, repo


@router.get('/projects/{project_id}/code/analysis')
def code_analysis(project_id: int, max_files: int = Query(250, ge=1, le=1000), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project, repo = _context(project_id, db, current_user)
    try:
        return code_analysis_service.analyze_repository(repo.repo_path, project, max_files)
    except (GitError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get('/projects/{project_id}/code/files')
def code_files(project_id: int, max_files: int = Query(250, ge=1, le=1000), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project, repo = _context(project_id, db, current_user)
    try:
        result = code_analysis_service.analyze_repository(repo.repo_path, project, max_files)
        return {'files': result['files'], 'files_analyzed': result['files_analyzed'], 'files_skipped': result['files_skipped']}
    except (GitError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get('/projects/{project_id}/code/changes/review')
def code_changes_review(project_id: int, max_files: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project, repo = _context(project_id, db, current_user)
    try:
        return code_analysis_service.changed_code_review(repo.repo_path, project, max_files)
    except (GitError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
