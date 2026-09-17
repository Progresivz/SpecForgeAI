from sqlalchemy.orm import Session
from app.models.workflow import EngineeringFinding, GeneratedTest, EngineeringActivity

def add_activity(db, project_id, user_id, action, summary, entity_type=None, entity_id=None, details=None):
    item=EngineeringActivity(project_id=project_id, actor_user_id=user_id, action=action, summary=summary, entity_type=entity_type, entity_id=entity_id, details=details)
    db.add(item); db.commit(); db.refresh(item); return item

def findings(db, project_id, status=None):
    q=db.query(EngineeringFinding).filter(EngineeringFinding.project_id==project_id)
    if status: q=q.filter(EngineeringFinding.status==status)
    return q.order_by(EngineeringFinding.created_at.desc()).all()

def get_finding(db, project_id, finding_id): return db.query(EngineeringFinding).filter(EngineeringFinding.project_id==project_id, EngineeringFinding.id==finding_id).first()
def tests(db, project_id): return db.query(GeneratedTest).filter(GeneratedTest.project_id==project_id).order_by(GeneratedTest.id.desc()).all()
def activities(db, project_id, limit=100): return db.query(EngineeringActivity).filter(EngineeringActivity.project_id==project_id).order_by(EngineeringActivity.created_at.desc()).limit(limit).all()
