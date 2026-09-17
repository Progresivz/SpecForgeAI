from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class GitRepository(Base):
    __tablename__ = "git_repositories"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    repo_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    project = relationship("Project", back_populates="git_repository")
