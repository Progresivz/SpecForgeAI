from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.datetime_utils import utcnow
from app.database.base import Base

class EngineeringFinding(Base):
    __tablename__ = 'engineering_findings'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    source = Column(String(40), nullable=False, default='code_review')
    severity = Column(String(20), nullable=False, default='medium')
    category = Column(String(60), nullable=False, default='general')
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default='')
    file_path = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default='open')
    linked_task_id = Column(Integer, ForeignKey('development_tasks.id', ondelete='SET NULL'), nullable=True)
    linked_maintenance_id = Column(Integer, ForeignKey('maintenance_items.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    project = relationship('Project')
    linked_task = relationship('DevelopmentTask')
    linked_maintenance = relationship('MaintenanceItem')

class GeneratedTest(Base):
    __tablename__ = 'generated_tests'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey('requirements.id', ondelete='SET NULL'), nullable=True)
    task_id = Column(Integer, ForeignKey('development_tasks.id', ondelete='SET NULL'), nullable=True)
    title = Column(String(200), nullable=False)
    test_type = Column(String(40), nullable=False, default='functional')
    priority = Column(String(20), nullable=False, default='medium')
    steps = Column(Text, nullable=False, default='')
    expected_result = Column(Text, nullable=False, default='')
    status = Column(String(20), nullable=False, default='proposed')
    source = Column(String(40), nullable=False, default='ai')
    created_at = Column(DateTime, default=utcnow, nullable=False)
    project = relationship('Project')
    requirement = relationship('Requirement')
    task = relationship('DevelopmentTask')

class EngineeringActivity(Base):
    __tablename__ = 'engineering_activities'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(80), nullable=False)
    entity_type = Column(String(60), nullable=True)
    entity_id = Column(Integer, nullable=True)
    summary = Column(String(500), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    project = relationship('Project')
    actor = relationship('User')

