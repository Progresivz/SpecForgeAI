from sqlalchemy.orm import Session

from app.models.task import DevelopmentTask
from app.schemas.task import DevelopmentTaskCreate, DevelopmentTaskUpdate


def _next_key(db: Session, project_id: int) -> str:
    count = db.query(DevelopmentTask).filter(DevelopmentTask.project_id == project_id).count()
    return f"TASK-{count + 1:04d}"


def get_tasks(db: Session, project_id: int, status: str | None = None, priority: str | None = None):
    query = db.query(DevelopmentTask).filter(DevelopmentTask.project_id == project_id)
    if status:
        query = query.filter(DevelopmentTask.status == status)
    if priority:
        query = query.filter(DevelopmentTask.priority == priority)
    return query.order_by(DevelopmentTask.id).all()


def get_task(db: Session, task_id: int, project_id: int):
    return db.query(DevelopmentTask).filter(
        DevelopmentTask.id == task_id,
        DevelopmentTask.project_id == project_id,
    ).first()


def _validate_links(db: Session, project_id: int, data):
    from app.models.milestone import Milestone
    from app.models.requirement import Requirement, UserStory
    from app.models.maintenance import MaintenanceItem

    checks = [
        (data.milestone_id, Milestone, "Milestone"),
        (data.requirement_id, Requirement, "Requirement"),
        (data.user_story_id, UserStory, "User story"),
        (data.maintenance_item_id, MaintenanceItem, "Maintenance item"),
    ]
    for value, model, label in checks:
        if value is not None and not db.query(model).filter(model.id == value, model.project_id == project_id).first():
            raise ValueError(f"{label} does not belong to this project")
    if data.depends_on_task_id is not None:
        if getattr(data, "id", None) == data.depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        dependency = get_task(db, data.depends_on_task_id, project_id)
        if not dependency:
            raise ValueError("Dependency task does not belong to this project")


def create_task(db: Session, project_id: int, data: DevelopmentTaskCreate) -> DevelopmentTask:
    _validate_links(db, project_id, data)
    item = DevelopmentTask(project_id=project_id, task_key=_next_key(db, project_id), **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_task(db: Session, item: DevelopmentTask, data: DevelopmentTaskUpdate) -> DevelopmentTask:
    values = data.model_dump(exclude_unset=True)
    # Validate foreign-key changes before mutating the entity.
    class Payload:
        pass
    payload = Payload()
    for name in ("milestone_id", "requirement_id", "user_story_id", "maintenance_item_id", "depends_on_task_id"):
        setattr(payload, name, values.get(name, getattr(item, name)))
    _validate_links(db, item.project_id, payload)
    for key, value in values.items():
        setattr(item, key, value)
    if item.status == "done":
        item.completed = True
    elif item.status in {"todo", "in_progress", "blocked", "cancelled"} and "completed" not in values:
        item.completed = False
    db.commit()
    db.refresh(item)
    return item


def delete_task(db: Session, item: DevelopmentTask):
    db.delete(item)
    db.commit()
