from datetime import datetime
from app.core.datetime_utils import utcnow
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.task import DevelopmentTask  # noqa: F401
from app.models.maintenance import MaintenanceItem  # noqa: F401
from app.models.requirement import Requirement  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.milestone import Milestone  # noqa: F401

class ReleaseAutomationRun(Base):
    __tablename__ = 'release_automation_runs'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    release_id = Column(Integer, ForeignKey('releases.id', ondelete='CASCADE'), nullable=False, index=True)
    release_notes = Column(Text, nullable=False, default='')
    test_suite = Column(Text, nullable=False, default='[]')
    ai_review = Column(Text, nullable=False, default='{}')
    decision = Column(String(30), nullable=False, default='no_go')
    score = Column(Integer, nullable=False, default=0)
    evidence = Column(Text, nullable=False, default='{}')
    created_at = Column(DateTime, default=utcnow, nullable=False)
    project = relationship('Project')
    release = relationship('Release')

