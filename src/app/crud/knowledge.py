from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeEntry
from app.models.project import Project
from app.schemas.knowledge import KnowledgeEntryCreate


def get_entries(db: Session, project_id: int, owner_id: int):
    return (db.query(KnowledgeEntry).join(Project, Project.id == KnowledgeEntry.project_id)
            .filter(KnowledgeEntry.project_id == project_id, Project.owner_id == owner_id)
            .order_by(KnowledgeEntry.id).all())


def get_entry(db: Session, entry_id: int, owner_id: int):
    return (db.query(KnowledgeEntry).join(Project, Project.id == KnowledgeEntry.project_id)
            .filter(KnowledgeEntry.id == entry_id, Project.owner_id == owner_id).first())


def upsert_entry(db: Session, project_id: int, data: KnowledgeEntryCreate):
    entry = (db.query(KnowledgeEntry)
             .filter(KnowledgeEntry.project_id == project_id,
                     KnowledgeEntry.source_type == data.source_type,
                     KnowledgeEntry.source_id == data.source_id).first())
    values = data.model_dump()
    values["tags"] = ",".join(dict.fromkeys(values["tags"]))
    if entry is None:
        entry = KnowledgeEntry(project_id=project_id, **values)
        db.add(entry)
    else:
        for key, value in values.items():
            setattr(entry, key, value)
    db.commit(); db.refresh(entry)
    return entry


def delete_entry(db: Session, entry: KnowledgeEntry):
    db.delete(entry); db.commit()
