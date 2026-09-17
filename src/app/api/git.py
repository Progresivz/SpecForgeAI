from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.git_repository import create_or_replace_repository, delete_repository, get_repository
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.schemas.git_repository import (GitChangelogResponse, GitCommit, GitCompareResponse, GitContributor, GitRepositoryCreate, GitRepositoryResponse, GitRiskResponse, GitStatusResponse, RollbackSuggestion)
from app.services import git_service

router = APIRouter(tags=["Version Control Monitor"])

def _repo(project_id, db, user):
    project=get_project(db,project_id,user.id)
    if not project: raise HTTPException(404,"Project not found")
    repo=get_repository(db,project_id,user.id)
    if not repo: raise HTTPException(404,"Git repository is not configured")
    if not repo.enabled: raise HTTPException(409,"Git repository monitoring is disabled")
    return repo

def _git_error(e): raise HTTPException(400,str(e))

@router.post('/projects/{project_id}/git/repository',response_model=GitRepositoryResponse,status_code=status.HTTP_201_CREATED)
def configure_git(project_id:int,data:GitRepositoryCreate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    project=get_project(db,project_id,current_user.id)
    if not project: raise HTTPException(404,"Project not found")
    try:
        path=git_service.configure_path(data.repo_path); git_service.status(path)
    except git_service.GitError as e: _git_error(e)
    data.repo_path=path
    return create_or_replace_repository(db,project,data)

@router.get('/projects/{project_id}/git/repository',response_model=GitRepositoryResponse)
def get_git(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user); return repo

@router.delete('/projects/{project_id}/git/repository',status_code=204)
def remove_git(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user); delete_repository(db,repo)

@router.get('/projects/{project_id}/git/status',response_model=GitStatusResponse)
def git_status(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.status(repo.repo_path)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/commits',response_model=list[GitCommit])
def git_commits(project_id:int,limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.commits(repo.repo_path,limit)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/contributors',response_model=list[GitContributor])
def git_contributors(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.contributors(repo.repo_path)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/changes',response_model=list)
def git_changes(project_id:int,base:str|None=None,head:str="HEAD",db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:
        return git_service.compare(repo.repo_path,base,head)["changes"] if base else git_service.status(repo.repo_path)["changes"]
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/compare',response_model=GitCompareResponse)
def git_compare(project_id:int,base:str,head:str="HEAD",db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.compare(repo.repo_path,base,head)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/changelog',response_model=GitChangelogResponse)
def git_changelog(project_id:int,limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.changelog(repo.repo_path,limit)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/risk',response_model=GitRiskResponse)
def git_risk(project_id:int,base:str|None=None,head:str="HEAD",db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.risk(repo.repo_path,base,head)
    except git_service.GitError as e:_git_error(e)

@router.get('/projects/{project_id}/git/rollback-suggestions',response_model=list[RollbackSuggestion])
def git_rollback(project_id:int,limit:int=Query(10,ge=1,le=100),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    repo=_repo(project_id,db,current_user)
    try:return git_service.rollback_suggestions(repo.repo_path,limit)
    except git_service.GitError as e:_git_error(e)
