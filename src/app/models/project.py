from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Not Started")

    owner = relationship("User", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan", order_by="Requirement.id")
    user_stories = relationship("UserStory", back_populates="project", cascade="all, delete-orphan", order_by="UserStory.id")
    database_design = relationship("DatabaseDesign", back_populates="project", uselist=False, cascade="all, delete-orphan")
    prototype_design = relationship("PrototypeDesign", back_populates="project", uselist=False, cascade="all, delete-orphan")
    documentation_set = relationship("DocumentationSet", back_populates="project", uselist=False, cascade="all, delete-orphan")
    git_repository = relationship("GitRepository", back_populates="project", uselist=False, cascade="all, delete-orphan")
    maintenance_items = relationship("MaintenanceItem", back_populates="project", cascade="all, delete-orphan", order_by="MaintenanceItem.id")
    use_cases = relationship("UseCase", back_populates="project", cascade="all, delete-orphan", order_by="UseCase.id")

    deadlines = relationship("Deadline", back_populates="project", cascade="all, delete-orphan", order_by="Deadline.due_date")
    knowledge_entries = relationship("KnowledgeEntry", back_populates="project", cascade="all, delete-orphan", order_by="KnowledgeEntry.id")
    ai_artifacts = relationship("AIArtifact", back_populates="project", cascade="all, delete-orphan", order_by="AIArtifact.id")
    development_tasks = relationship("DevelopmentTask", back_populates="project", cascade="all, delete-orphan", order_by="DevelopmentTask.id")

    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan", order_by="Milestone.due_date")
    copilot_conversations = relationship("CopilotConversation", back_populates="project", cascade="all, delete-orphan", order_by="CopilotConversation.id")

