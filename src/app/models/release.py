from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class SDLCTtraceLink(Base):
    __tablename__ = 'sdlc_trace_links'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    relation = Column(String(40), nullable=False, default='implements')
    confidence = Column(Integer, nullable=False, default=100)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    project = relationship('Project')

class Release(Base):
    __tablename__ = 'releases'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default='')
    status = Column(String(30), nullable=False, default='draft')
    target_date = Column(DateTime, nullable=True)
    readiness_score = Column(Integer, nullable=False, default=0)
    gate_status = Column(String(30), nullable=False, default='blocked')
    gate_report = Column(Text, nullable=False, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    project = relationship('Project')
