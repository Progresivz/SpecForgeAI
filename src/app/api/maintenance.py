from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.maintenance import create_item, delete_item, get_item, get_items, update_item
from app.database.deps import get_db
from app.models.user import User
from app.schemas.maintenance import MaintenanceItemCreate, MaintenanceItemResponse, MaintenanceItemUpdate, MaintenanceReportResponse, RefactoringRecommendation
from app.services.maintenance_service import refactoring_recommendations, report

router=APIRouter(tags=["Maintenance AI"])

def _project(db,pid,user):
    p=get_project(db,pid,user.id)
    if not p: raise HTTPException(404,"Project not found")
    return p

def _item(db,iid,pid):
    item=get_item(db,iid,pid)
    if not item: raise HTTPException(404,"Maintenance item not found")
    return item

@router.post('/projects/{project_id}/maintenance',response_model=MaintenanceItemResponse,status_code=status.HTTP_201_CREATED)
def add_maintenance(project_id:int,data:MaintenanceItemCreate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); return create_item(db,project_id,data)

@router.get('/projects/{project_id}/maintenance',response_model=list[MaintenanceItemResponse])
def list_maintenance(project_id:int,status_filter:str|None=Query(None,alias='status'),item_type:str|None=None,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); return get_items(db,project_id,status_filter,item_type)

@router.get('/projects/{project_id}/maintenance/report',response_model=MaintenanceReportResponse)
def maintenance_report(project_id:int,limit:int=Query(10,ge=1,le=50),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    p=_project(db,project_id,current_user); return report(p,get_items(db,project_id),limit)

@router.get('/projects/{project_id}/maintenance/refactoring',response_model=list[RefactoringRecommendation])
def maintenance_refactoring(project_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _project(db,project_id,current_user); return refactoring_recommendations(get_items(db,project_id))

@router.put('/maintenance/{item_id}',response_model=MaintenanceItemResponse)
def edit_maintenance(item_id:int,data:MaintenanceItemUpdate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    # Ownership is enforced through the project lookup after finding the item.
    item=db.query(__import__('app.models.maintenance',fromlist=['MaintenanceItem']).MaintenanceItem).filter_by(id=item_id).first()
    if not item: raise HTTPException(404,"Maintenance item not found")
    _project(db,item.project_id,current_user); return update_item(db,item,data)

@router.delete('/maintenance/{item_id}',status_code=204)
def remove_maintenance(item_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    item=db.query(__import__('app.models.maintenance',fromlist=['MaintenanceItem']).MaintenanceItem).filter_by(id=item_id).first()
    if not item: raise HTTPException(404,"Maintenance item not found")
    _project(db,item.project_id,current_user); delete_item(db,item)
