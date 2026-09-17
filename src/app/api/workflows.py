from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.workflow import findings, get_finding, tests, activities
from app.database.deps import get_db
from app.models.user import User
from app.schemas.workflow import FindingResponse, FindingUpdate, TestResponse, ActivityResponse
from app.services.change_impact_service import build_impact
from app.crud.git_repository import get_repository
from app.services.workflow_service import materialize_findings, create_work_items, generate_tests
from app.services.ai_service import generate
from app.models.workflow import GeneratedTest

router=APIRouter(prefix='/projects/{project_id}/workflows',tags=['Engineering Workflows'])
def ctx(db,pid,user):
    p=get_project(db,pid,user.id)
    if not p: raise HTTPException(404,'Project not found')
    repo=get_repository(db,pid,user.id)
    if not repo or not repo.enabled: raise HTTPException(409,'Git repository is not configured or is disabled')
    return p,repo

@router.post('/findings',response_model=list[FindingResponse])
def create_findings(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p,repo=ctx(db,project_id,current_user)
    return materialize_findings(db,p,current_user.id,build_impact(repo.repo_path,p))

@router.get('/findings',response_model=list[FindingResponse])
def list_findings(project_id:int,status:str|None=Query(None),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=get_project(db,project_id,current_user.id)
    if not p: raise HTTPException(404,'Project not found')
    return findings(db,project_id,status)

@router.put('/findings/{finding_id}',response_model=FindingResponse)
def update_finding(project_id:int,finding_id:int,payload:FindingUpdate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=get_project(db,project_id,current_user.id)
    if not p: raise HTTPException(404,'Project not found')
    item=get_finding(db,project_id,finding_id)
    if not item: raise HTTPException(404,'Finding not found')
    item.status=payload.status; db.commit(); db.refresh(item); return item

@router.post('/tasks-from-impact')
def tasks_from_impact(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p,repo=ctx(db,project_id,current_user); return {'created':create_work_items(db,p,current_user.id,build_impact(repo.repo_path,p))}

@router.post('/tests',response_model=list[TestResponse])
def generate_test_workflow(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p,repo=ctx(db,project_id,current_user); return generate_tests(db,p,current_user.id,build_impact(repo.repo_path,p))

@router.get('/tests',response_model=list[TestResponse])
def list_tests(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=get_project(db,project_id,current_user.id)
    if not p: raise HTTPException(404,'Project not found')
    return tests(db,project_id)

@router.get('/activity',response_model=list[ActivityResponse])
def activity(project_id:int,limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=get_project(db,project_id,current_user.id)
    if not p: raise HTTPException(404,'Project not found')
    return activities(db,project_id,limit)

@router.post('/ai-tests', response_model=TestResponse)
def ai_test(project_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    p,repo=ctx(db,project_id,current_user)
    impact=build_impact(repo.repo_path,p)
    prompt = "Act as a senior QA engineer. Generate one concise, executable regression test plan for the current code changes. Include title, test type, priority, numbered steps, and expected result. Use only the supplied impact context and do not invent behavior.\n\n" + str(impact)
    try:
        result=generate(db,p,prompt,knowledge_query='testing requirements',max_output_tokens=1800)
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
    item=GeneratedTest(project_id=p.id,title='AI code-change regression test',test_type='regression',priority='high',steps=result.content,expected_result='The changed behavior passes the generated regression checks without violating linked requirements.',source='ai')
    db.add(item); db.commit(); db.refresh(item)
    from app.crud.workflow import add_activity
    add_activity(db,p.id,current_user.id,'ai_test_generated', 'Generated an AI-assisted regression test proposal.','generated_test',item.id, result.provider+'/'+result.model)
    return item
