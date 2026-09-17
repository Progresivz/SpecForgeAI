from sqlalchemy.orm import Session, joinedload

from app.models.database_design import DatabaseColumn, DatabaseDesign, DatabaseRelationship, DatabaseTable
from app.models.project import Project
from app.schemas.database_design import DatabaseDesignCreate


def get_design(db: Session, project_id: int, owner_id: int):
    return (
        db.query(DatabaseDesign)
        .join(Project, Project.id == DatabaseDesign.project_id)
        .options(joinedload(DatabaseDesign.tables).joinedload(DatabaseTable.columns), joinedload(DatabaseDesign.relationships))
        .filter(DatabaseDesign.project_id == project_id, Project.owner_id == owner_id)
        .first()
    )


def create_or_replace_design(db: Session, project: Project, data: DatabaseDesignCreate) -> DatabaseDesign:
    existing = db.query(DatabaseDesign).filter(DatabaseDesign.project_id == project.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    design = DatabaseDesign(project_id=project.id, name=data.name, target_dialect=data.target_dialect.lower(), notes=data.notes)
    db.add(design)
    db.flush()

    for table_data in data.tables:
        table = DatabaseTable(design_id=design.id, name=table_data.name, description=table_data.description)
        db.add(table)
        db.flush()
        for column_data in table_data.columns:
            db.add(DatabaseColumn(table_id=table.id, **column_data.model_dump()))

    for relationship in data.relationships:
        db.add(DatabaseRelationship(design_id=design.id, **relationship.model_dump()))

    db.commit()
    return get_design(db, project.id, project.owner_id)


def delete_design(db: Session, design: DatabaseDesign) -> None:
    db.delete(design)
    db.commit()
