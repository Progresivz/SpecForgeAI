from sqlalchemy.orm import Session

from app.models.milestone import Milestone
from app.models.project import Project
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate


def create_milestone(db: Session, project: Project, milestone: MilestoneCreate) -> Milestone:
    db_milestone = Milestone(project_id=project.id, **milestone.model_dump())
    db.add(db_milestone)
    db.commit()
    db.refresh(db_milestone)
    return db_milestone


def get_milestones(db: Session, project_id: int):
    return db.query(Milestone).filter(Milestone.project_id == project_id).order_by(Milestone.due_date).all()


def get_milestone(db: Session, milestone_id: int, owner_id: int):
    return (
        db.query(Milestone)
        .join(Project, Project.id == Milestone.project_id)
        .filter(Milestone.id == milestone_id, Project.owner_id == owner_id)
        .first()
    )


def update_milestone(db: Session, milestone: Milestone, updates: MilestoneUpdate) -> Milestone:
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(milestone, key, value)
    db.commit()
    db.refresh(milestone)
    return milestone


def delete_milestone(db: Session, milestone: Milestone) -> None:
    db.delete(milestone)
    db.commit()
