from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, project: ProjectCreate, owner_id: int) -> Project:
    db_project = Project(**project.model_dump(), owner_id=owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_projects(db: Session, owner_id: int):
    return db.query(Project).filter(Project.owner_id == owner_id).order_by(Project.id.desc()).all()


def get_project(db: Session, project_id: int, owner_id: int):
    return db.query(Project).filter(Project.id == project_id, Project.owner_id == owner_id).first()


def update_project(db: Session, project: Project, updates: ProjectUpdate) -> Project:
    values = updates.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(project, key, value)
    if project.target_date < project.start_date:
        raise ValueError("target_date cannot be before start_date")
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
