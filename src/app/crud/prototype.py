from sqlalchemy.orm import Session, joinedload
from app.models.project import Project
from app.models.prototype import PrototypeDesign, PrototypeScreen, PrototypeComponent, PrototypeFlow
from app.schemas.prototype import PrototypeDesignCreate

def get_design(db: Session, project_id: int, owner_id: int):
    return (db.query(PrototypeDesign).join(Project, Project.id == PrototypeDesign.project_id)
        .options(joinedload(PrototypeDesign.screens).joinedload(PrototypeScreen.components), joinedload(PrototypeDesign.flows))
        .filter(PrototypeDesign.project_id == project_id, Project.owner_id == owner_id).first())

def create_or_replace_design(db: Session, project: Project, data: PrototypeDesignCreate):
    existing = db.query(PrototypeDesign).filter(PrototypeDesign.project_id == project.id).first()
    if existing: db.delete(existing); db.flush()
    design = PrototypeDesign(project_id=project.id, name=data.name, description=data.description, style_notes=data.style_notes)
    db.add(design); db.flush()
    for i, screen_data in enumerate(data.screens):
        vals = screen_data.model_dump(exclude={'components'})
        vals['position'] = i
        screen = PrototypeScreen(design_id=design.id, **vals); db.add(screen); db.flush()
        for j, comp in enumerate(screen_data.components):
            db.add(PrototypeComponent(screen_id=screen.id, position=j, **comp.model_dump()))
    for flow in data.flows: db.add(PrototypeFlow(design_id=design.id, **flow.model_dump()))
    db.commit(); return get_design(db, project.id, project.owner_id)

def delete_design(db: Session, design: PrototypeDesign):
    db.delete(design); db.commit()
