from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database.base import Base

class DocumentationSet(Base):
    __tablename__ = 'documentation_sets'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default='')
    project = relationship('Project', back_populates='documentation_set')
    documents = relationship('DocumentationDocument', back_populates='documentation_set', cascade='all, delete-orphan', order_by='DocumentationDocument.id')

class DocumentationDocument(Base):
    __tablename__ = 'documentation_documents'
    id = Column(Integer, primary_key=True, index=True)
    documentation_set_id = Column(ForeignKey('documentation_sets.id', ondelete='CASCADE'), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content_markdown = Column(Text, nullable=False, default='')
    documentation_set = relationship('DocumentationSet', back_populates='documents')
