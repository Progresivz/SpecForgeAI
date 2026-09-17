from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    deadline_type: Mapped[str] = mapped_column(String(30), nullable=False, default="milestone")
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estimated_work_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alert_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    project = relationship("Project", back_populates="deadlines")
