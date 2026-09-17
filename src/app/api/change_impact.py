from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.git_repository import get_repository
from app.crud.project import get_project
from app.database.deps import get_db
from app.models.user import User
from app.services.change_impact_service import build_impact, build_diff_context
from app.services.ai_service import generate
from app.services.git_service import GitError
router=APIRouter(tags=["Code Change Intelligence"])
def _context(project_id,db,user):
    project=get_project(db,project_id,user.id)
    if not project: raise HTTPException(404,"Project not found")
    repo=get_repository(db,project_id,user.id)
    if not repo or not repo.enabled: raise HTTPException(409,"Git repository is not configured or is disabled")
    return project,repo
@router.get('/projects/{project_id}/code/changes/diff')
def code_diff(project_id:int,base:str=Query('HEAD',min_length=1,max_length=200),max_chars:int=Query(120000,ge=1000,le=500000),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    project,repo=_context(project_id,db,current_user)
    try:return build_diff_context(repo.repo_path,project,base,max_chars)
    except (GitError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc
@router.get('/projects/{project_id}/code/changes/impact')
def code_impact(project_id:int,max_files:int=Query(100,ge=1,le=500),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    project,repo=_context(project_id,db,current_user)
    try:return build_impact(repo.repo_path,project,max_files)
    except (GitError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc
@router.post('/projects/{project_id}/code/changes/ai-review')
def code_ai_review(project_id:int,base:str=Query('HEAD',min_length=1,max_length=200),max_chars:int=Query(80000,ge=1000,le=200000),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    project,repo=_context(project_id,db,current_user)
    try: context=build_diff_context(repo.repo_path,project,base,max_chars)
    except (GitError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc
    prompt=("Act as a senior software engineer performing a read-only code-change review. Review ONLY the supplied Git diff and impact context. Identify correctness bugs, security issues, regressions, missing tests, and requirement/task impact. Do not claim a defect unless supported by the diff; distinguish uncertainty. Return prioritized findings with file/line references when present, then recommended tests and a concise overall risk assessment.\n\nGIT DIFF:\n"+context['diff']+"\n\nCHANGE IMPACT:\n"+str(context['impact']))
    try: result=generate(db,project,prompt,include_knowledge=True,max_output_tokens=3500)
    except RuntimeError as exc: raise HTTPException(503,str(exc)) from exc
    return {'project_id':project_id,'base':base,'provider':result.provider,'model':result.model,'review':result.content,'impact':context['impact'],'diff_truncated':context['truncated']}
