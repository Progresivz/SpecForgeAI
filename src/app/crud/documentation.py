from sqlalchemy.orm import Session, joinedload
from app.models.documentation import DocumentationSet

def get_documentation(db: Session, project_id: int, owner_id: int):
    return (db.query(DocumentationSet)
            .options(joinedload(DocumentationSet.documents))
            .join(DocumentationSet.project)
            .filter(DocumentationSet.project_id == project_id, DocumentationSet.project.has(owner_id=owner_id)).first())

def create_or_replace(db: Session, project, data):
    existing = get_documentation(db, project.id, project.owner_id)
    if existing: db.delete(existing); db.flush()
    docset=DocumentationSet(project_id=project.id, name=data.name, description=data.description)
    for d in data.documents:
        docset.documents.append(__import__('app.models.documentation', fromlist=['DocumentationDocument']).DocumentationDocument(**d.model_dump()))
    db.add(docset); db.commit(); db.refresh(docset); return get_documentation(db, project.id, project.owner_id)

def delete_documentation(db, docset):
    db.delete(docset); db.commit()
