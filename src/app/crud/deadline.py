from sqlalchemy.orm import Session

from app.models.deadline import Deadline
from app.models.project import Project
from app.schemas.deadline import DeadlineCreate, DeadlineUpdate


def get_deadlines(db: Session, project_id: int, owner_id: int):
    return (
        db.query(Deadline)
        .join(Project, Project.id == Deadline.project_id)
        .filter(Deadline.project_id == project_id, Project.owner_id == owner_id)
        .order_by(Deadline.due_date, Deadline.id)
        .all()
    )


def get_deadline(db: Session, deadline_id: int, owner_id: int):
    return (
        db.query(Deadline)
        .join(Project, Project.id == Deadline.project_id)
        .filter(Deadline.id == deadline_id, Project.owner_id == owner_id)
        .first()
    )


def create_deadline(db: Session, project: Project, data: DeadlineCreate) -> Deadline:
    deadline = Deadline(project_id=project.id, **data.model_dump())
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def update_deadline(db: Session, deadline: Deadline, data: DeadlineUpdate) -> Deadline:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(deadline, key, value)
    db.commit()
    db.refresh(deadline)
    return deadline


def delete_deadline(db: Session, deadline: Deadline) -> None:
    db.delete(deadline)
    db.commit()
