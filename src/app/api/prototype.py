from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.crud.project import get_project
from app.crud.prototype import create_or_replace_design, delete_design, get_design
from app.database.deps import get_db
from app.models.user import User
from app.schemas.prototype import PrototypeDesignCreate, PrototypeDesignResponse, PrototypeSpecResponse
from app.services.prototype_service import generate_prototype

router = APIRouter(tags=['Prototype Designer'])

def _project_or_404(db, project_id, user):
    project=get_project(db, project_id, user.id)
    if not project: raise HTTPException(status_code=404, detail='Project not found')
    return project

@router.post('/projects/{project_id}/prototype', response_model=PrototypeDesignResponse, status_code=status.HTTP_201_CREATED)
def create_prototype(project_id:int, data:PrototypeDesignCreate, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    project=_project_or_404(db, project_id, current_user)
    return create_or_replace_design(db, project, data)

@router.get('/projects/{project_id}/prototype', response_model=PrototypeDesignResponse)
def get_prototype(project_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    _project_or_404(db, project_id, current_user); design=get_design(db, project_id, current_user.id)
    if not design: raise HTTPException(status_code=404, detail='Prototype design not found')
    return design

@router.delete('/projects/{project_id}/prototype', status_code=status.HTTP_204_NO_CONTENT)
def remove_prototype(project_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    _project_or_404(db, project_id, current_user); design=get_design(db, project_id, current_user.id)
    if not design: raise HTTPException(status_code=404, detail='Prototype design not found')
    delete_design(db, design)

@router.post('/projects/{project_id}/prototype/generate', response_model=PrototypeSpecResponse)
def generate_prototype_spec(project_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    project=_project_or_404(db, project_id, current_user)
    generated=generate_prototype(project, db)
    data=PrototypeDesignCreate(name=f'{project.name} UI Prototype', description='Generated from project requirements and use cases.', screens=generated['screens'], flows=generated['flows'])
    design=create_or_replace_design(db, project, data)
    return PrototypeSpecResponse(project_id=project.id, project_name=project.name, summary_markdown=generated['summary_markdown'])
