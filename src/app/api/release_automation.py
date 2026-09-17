import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.release import get_release
from app.database.deps import get_db
from app.models.user import User
from app.models.release_automation import ReleaseAutomationRun
from app.schemas.release_automation import ReleaseAutomationResponse
from app.services.release_automation_service import run_automation
from app.crud.workflow import add_activity

router=APIRouter(prefix='/projects/{project_id}/release', tags=['Release Automation'])

def _ctx(db,pid,rid,user):
    p=get_project(db,pid,user.id)
    if not p: raise HTTPException(404,'Project not found')
    r=get_release(db,pid,rid)
    if not r: raise HTTPException(404,'Release not found')
    return p,r

@router.post('/{release_id}/automation', response_model=ReleaseAutomationResponse)
def automation(project_id:int, release_id:int, include_ai:bool=False, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    p,r=_ctx(db,project_id,release_id,current_user)
    run=run_automation(db,p,r,include_ai=include_ai)
    add_activity(db,p.id,current_user.id,'release_automation_run',f'Generated release automation evidence for {r.version}: {run.decision}.','release_automation',run.id)
    return run

@router.get('/{release_id}/automation', response_model=list[ReleaseAutomationResponse])
def automation_history(project_id:int, release_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    _ctx(db,project_id,release_id,current_user)
    return db.query(ReleaseAutomationRun).filter(ReleaseAutomationRun.project_id==project_id, ReleaseAutomationRun.release_id==release_id).order_by(ReleaseAutomationRun.created_at.desc()).all()

@router.get('/{release_id}/go-no-go')
def go_no_go(project_id:int, release_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    p,r=_ctx(db,project_id,release_id,current_user)
    latest=db.query(ReleaseAutomationRun).filter(ReleaseAutomationRun.project_id==project_id,ReleaseAutomationRun.release_id==release_id).order_by(ReleaseAutomationRun.created_at.desc()).first()
    if not latest:
        latest=run_automation(db,p,r,include_ai=False)
    return {'release_id':r.id,'version':r.version,'decision':latest.decision,'score':latest.score,'readiness_score':r.readiness_score,'gate_status':r.gate_status,'ai_review':json.loads(latest.ai_review),'evidence':json.loads(latest.evidence)}
