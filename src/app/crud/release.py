from sqlalchemy.orm import Session
from app.models.release import SDLCTtraceLink, Release

def create_trace(db, project_id, data):
    item=SDLCTtraceLink(project_id=project_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

def list_traces(db, project_id):
    return db.query(SDLCTtraceLink).filter(SDLCTtraceLink.project_id==project_id).order_by(SDLCTtraceLink.id.desc()).all()

def create_release(db, project_id, data):
    item=Release(project_id=project_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

def list_releases(db, project_id):
    return db.query(Release).filter(Release.project_id==project_id).order_by(Release.id.desc()).all()

def get_release(db, project_id, release_id):
    return db.query(Release).filter(Release.project_id==project_id, Release.id==release_id).first()
