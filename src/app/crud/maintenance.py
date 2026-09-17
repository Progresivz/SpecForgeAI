from sqlalchemy.orm import Session
from app.models.maintenance import MaintenanceItem
from app.schemas.maintenance import MaintenanceItemCreate, MaintenanceItemUpdate

def create_item(db: Session, project_id: int, data: MaintenanceItemCreate) -> MaintenanceItem:
    item = MaintenanceItem(project_id=project_id, **data.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item

def get_items(db: Session, project_id: int, status: str | None = None, item_type: str | None = None):
    q = db.query(MaintenanceItem).filter(MaintenanceItem.project_id == project_id)
    if status: q = q.filter(MaintenanceItem.status == status)
    if item_type: q = q.filter(MaintenanceItem.item_type == item_type)
    return q.order_by(MaintenanceItem.id.desc()).all()

def get_item(db: Session, item_id: int, project_id: int):
    return db.query(MaintenanceItem).filter(MaintenanceItem.id == item_id, MaintenanceItem.project_id == project_id).first()

def update_item(db: Session, item: MaintenanceItem, data: MaintenanceItemUpdate):
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

def delete_item(db: Session, item: MaintenanceItem):
    db.delete(item); db.commit()
