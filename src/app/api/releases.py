import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.release import create_release, get_release, list_releases, create_trace, list_traces
from app.database.deps import get_db
from app.models.user import User
from app.schemas.release import ReleaseCreate, ReleaseUpdate, ReleaseResponse, TraceLinkCreate, TraceLinkResponse
from app.services.release_service import build_traceability, release_gate_report
from app.crud.workflow import add_activity

router=APIRouter(prefix='/projects/{project_id}/release', tags=['Release Management'])
def _project(db,pid,user):
    p=get_project(db,pid,user.id)
    if not p: raise HTTPException(404,'Project not found')
    return p

@router.post('/traceability/build', response_model=list[TraceLinkResponse])
def build(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); created=build_traceability(db,p)
    add_activity(db,p.id,current_user.id,'traceability_built',f'Built {len(created)} SDLC traceability link(s).','traceability',None)
    return created

@router.get('/traceability', response_model=list[TraceLinkResponse])
def traces(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); return list_traces(db,project_id)

@router.get('/readiness')
def readiness(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    return release_gate_report(db,_project(db,project_id,current_user))

@router.post('', response_model=ReleaseResponse, status_code=201)
def create(project_id:int,payload:ReleaseCreate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); item=create_release(db,project_id,payload); report=release_gate_report(db,p,item); item.readiness_score=report['readiness_score']; item.gate_status=report['gate_status']; item.gate_report=json.dumps(report); db.commit(); db.refresh(item)
    add_activity(db,p.id,current_user.id,'release_created',f'Created release {item.version}.','release',item.id)
    return item

@router.get('', response_model=list[ReleaseResponse])
def releases(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); return list_releases(db,project_id)

@router.get('/{release_id}', response_model=ReleaseResponse)
def release(project_id:int,release_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); item=get_release(db,project_id,release_id)
    if not item: raise HTTPException(404,'Release not found')
    return item

@router.post('/{release_id}/evaluate', response_model=ReleaseResponse)
def evaluate(project_id:int,release_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); item=get_release(db,project_id,release_id)
    if not item: raise HTTPException(404,'Release not found')
    report=release_gate_report(db,p,item); item.readiness_score=report['readiness_score']; item.gate_status=report['gate_status']; item.gate_report=json.dumps(report); db.commit(); db.refresh(item)
    add_activity(db,p.id,current_user.id,'release_evaluated',f'Evaluated release {item.version}: {item.gate_status}.','release',item.id)
    return item

@router.post('/{release_id}/promote', response_model=ReleaseResponse)
def promote(project_id:int,release_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); item=get_release(db,project_id,release_id)
    if not item: raise HTTPException(404,'Release not found')
    report=release_gate_report(db,p,item); item.readiness_score=report['readiness_score']; item.gate_status=report['gate_status']; item.gate_report=json.dumps(report)
    if not report['ready']: db.commit(); raise HTTPException(409, {'message':'Release gates are not satisfied.','readiness':report})
    item.status='ready'; db.commit(); db.refresh(item); add_activity(db,p.id,current_user.id,'release_promoted',f'Release {item.version} passed all readiness gates.','release',item.id); return item
