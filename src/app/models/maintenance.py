from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database.base import Base

class MaintenanceItem(Base):
    __tablename__ = "maintenance_items"

    from sqlalchemy import Column
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(30), nullable=False, default="bug")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    severity = Column(String(20), nullable=False, default="medium")
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")
    affected_area = Column(String(200), nullable=True)
    source = Column(String(200), nullable=True)
    effort = Column(String(20), nullable=True)
    resolution = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)

    project = relationship("Project", back_populates="maintenance_items")
