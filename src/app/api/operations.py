from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.database.deps import get_db
from app.models.operations import BackupRecord, OperationalJob
from app.schemas.operations import BackupResponse, OperationJobResponse, RetentionResponse
from app.services.backup_service import run_backup, apply_retention, backup_status, verify_backup

router=APIRouter(prefix='/operations', tags=['Operations'], dependencies=[Depends(get_current_user)])

@router.post('/backups', response_model=BackupResponse)
def create_backup(db:Session=Depends(get_db)):
    return run_backup(db)

@router.get('/backups', response_model=list[BackupResponse])
def list_backups(limit:int=20, db:Session=Depends(get_db)):
    limit=max(1,min(limit,100)); return db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(limit).all()

@router.post('/backups/retention', response_model=RetentionResponse)
def retention(db:Session=Depends(get_db)):
    return apply_retention(db)

@router.post('/backups/{backup_id}/verify')
def verify(backup_id:int, db:Session=Depends(get_db)):
    record=db.get(BackupRecord,backup_id)
    if not record: raise HTTPException(404,'Backup not found')
    ok,msg=verify_backup(__import__('pathlib').Path(record.path),record.database_type)
    record.verified=ok; record.status='success' if ok else 'unverified'; record.message=msg; db.commit()
    return {'backup_id':backup_id,'verified':ok,'message':msg}

@router.get('/status')
def status(db:Session=Depends(get_db)):
    data=backup_status(db); latest=data.pop('latest',None); data['latest']=BackupResponse.model_validate(latest).model_dump() if latest else None; return data

@router.get('/jobs', response_model=list[OperationJobResponse])
def jobs(limit:int=20, db:Session=Depends(get_db)):
    limit=max(1,min(limit,100)); return db.query(OperationalJob).order_by(OperationalJob.started_at.desc()).limit(limit).all()
