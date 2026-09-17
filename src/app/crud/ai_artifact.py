from sqlalchemy.orm import Session
from app.models.ai_artifact import AIArtifact


def get_artifact(db: Session, artifact_id: int, owner_id: int):
    return (db.query(AIArtifact)
            .join(AIArtifact.project)
            .filter(AIArtifact.id == artifact_id, AIArtifact.project.has(owner_id=owner_id))
            .first())


def list_artifacts(db: Session, project_id: int, owner_id: int, artifact_type: str | None = None):
    q = (db.query(AIArtifact).join(AIArtifact.project)
         .filter(AIArtifact.project_id == project_id, AIArtifact.project.has(owner_id=owner_id)))
    if artifact_type:
        q = q.filter(AIArtifact.artifact_type == artifact_type)
    return q.order_by(AIArtifact.id.desc()).all()


def create_artifact(db: Session, project_id: int, result, artifact_type: str, title: str):
    artifact = AIArtifact(project_id=project_id, artifact_type=artifact_type, title=title,
                          content=result.content, provider=result.provider, model=result.model)
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact
