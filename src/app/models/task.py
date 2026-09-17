from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class DevelopmentTask(Base):
    __tablename__ = "development_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    user_story_id = Column(Integer, ForeignKey("user_stories.id", ondelete="SET NULL"), nullable=True, index=True)
    maintenance_item_id = Column(Integer, ForeignKey("maintenance_items.id", ondelete="SET NULL"), nullable=True, index=True)
    depends_on_task_id = Column(Integer, ForeignKey("development_tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    task_key = Column(String(30), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    task_type = Column(String(30), nullable=False, default="development")
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="todo")
    estimate_hours = Column(Integer, nullable=True)
    due_date = Column(Date, nullable=True)
    completed = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="development_tasks")
    milestone = relationship("Milestone")
    requirement = relationship("Requirement")
    user_story = relationship("UserStory")
    maintenance_item = relationship("MaintenanceItem")
    depends_on = relationship("DevelopmentTask", remote_side=[id], uselist=False)
