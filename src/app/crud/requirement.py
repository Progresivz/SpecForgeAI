from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.requirement import AcceptanceCriterion, Requirement, TraceabilityLink, UseCase, UserStory
from app.schemas.requirement import (
    AcceptanceCriterionCreate,
    RequirementCreate,
    RequirementUpdate,
    TraceabilityLinkCreate,
    UseCaseCreate,
    UseCaseUpdate,
    UserStoryCreate,
    UserStoryUpdate,
)


def _next_id(db: Session, model, project_id: int, prefix: str) -> str:
    count = db.query(model).filter(model.project_id == project_id).count() + 1
    return f"{prefix}-{count:03d}"


def get_requirement(db: Session, requirement_id: int, owner_id: int):
    return (
        db.query(Requirement)
        .join(Project, Project.id == Requirement.project_id)
        .filter(Requirement.id == requirement_id, Project.owner_id == owner_id)
        .first()
    )


def get_requirements(db: Session, project_id: int):
    return db.query(Requirement).filter(Requirement.project_id == project_id).order_by(Requirement.id).all()


def create_requirement(db: Session, project: Project, data: RequirementCreate) -> Requirement:
    criteria = data.acceptance_criteria
    values = data.model_dump(exclude={"acceptance_criteria"})
    requirement = Requirement(
        project_id=project.id,
        requirement_id=_next_id(db, Requirement, project.id, "FR" if values["requirement_type"] == "functional" else "NFR"),
        **values,
    )
    db.add(requirement)
    db.flush()
    for criterion in criteria:
        db.add(AcceptanceCriterion(requirement_id=requirement.id, **criterion.model_dump()))
    db.commit()
    db.refresh(requirement)
    return requirement


def update_requirement(db: Session, requirement: Requirement, data: RequirementUpdate) -> Requirement:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(requirement, key, value)
    db.commit()
    db.refresh(requirement)
    return requirement


def delete_requirement(db: Session, requirement: Requirement) -> None:
    db.delete(requirement)
    db.commit()


def add_acceptance_criterion(db: Session, requirement: Requirement, data: AcceptanceCriterionCreate):
    criterion = AcceptanceCriterion(requirement_id=requirement.id, **data.model_dump())
    db.add(criterion)
    db.commit()
    db.refresh(criterion)
    return criterion


def get_user_stories(db: Session, project_id: int):
    return db.query(UserStory).filter(UserStory.project_id == project_id).order_by(UserStory.id).all()


def get_user_story(db: Session, story_id: int, owner_id: int):
    return (
        db.query(UserStory).join(Project, Project.id == UserStory.project_id)
        .filter(UserStory.id == story_id, Project.owner_id == owner_id).first()
    )


def create_user_story(db: Session, project: Project, data: UserStoryCreate) -> UserStory:
    story = UserStory(project_id=project.id, story_id=_next_id(db, UserStory, project.id, "US"), **data.model_dump())
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def update_user_story(db: Session, story: UserStory, data: UserStoryUpdate) -> UserStory:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(story, key, value)
    db.commit()
    db.refresh(story)
    return story


def delete_user_story(db: Session, story: UserStory) -> None:
    db.delete(story)
    db.commit()


def get_use_cases(db: Session, project_id: int):
    return db.query(UseCase).filter(UseCase.project_id == project_id).order_by(UseCase.id).all()


def get_use_case(db: Session, use_case_id: int, owner_id: int):
    return (
        db.query(UseCase).join(Project, Project.id == UseCase.project_id)
        .filter(UseCase.id == use_case_id, Project.owner_id == owner_id).first()
    )


def create_use_case(db: Session, project: Project, data: UseCaseCreate) -> UseCase:
    case = UseCase(project_id=project.id, use_case_id=_next_id(db, UseCase, project.id, "UC"), **data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update_use_case(db: Session, case: UseCase, data: UseCaseUpdate) -> UseCase:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


def delete_use_case(db: Session, case: UseCase) -> None:
    db.delete(case)
    db.commit()


def get_traceability(db: Session, project_id: int):
    return (
        db.query(TraceabilityLink)
        .join(Requirement, Requirement.id == TraceabilityLink.requirement_id)
        .filter(Requirement.project_id == project_id)
        .order_by(TraceabilityLink.id).all()
    )


def create_traceability(db: Session, data: TraceabilityLinkCreate, owner_id: int) -> TraceabilityLink:
    requirement = get_requirement(db, data.requirement_id, owner_id)
    if not requirement:
        raise ValueError("Requirement not found")
    if data.user_story_id:
        story = get_user_story(db, data.user_story_id, owner_id)
        if not story or story.project_id != requirement.project_id:
            raise ValueError("User story not found in the same project")
    if data.use_case_id:
        case = get_use_case(db, data.use_case_id, owner_id)
        if not case or case.project_id != requirement.project_id:
            raise ValueError("Use case not found in the same project")
    link = TraceabilityLink(**data.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
