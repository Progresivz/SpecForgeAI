from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(String(30), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirement_type = Column(String(30), nullable=False, default="functional")
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="draft")
    rationale = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)

    project = relationship("Project", back_populates="requirements")
    acceptance_criteria = relationship(
        "AcceptanceCriterion", back_populates="requirement", cascade="all, delete-orphan", order_by="AcceptanceCriterion.id"
    )
    trace_links = relationship(
        "TraceabilityLink", back_populates="requirement", cascade="all, delete-orphan", order_by="TraceabilityLink.id"
    )


class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion = Column(Text, nullable=False)
    is_met = Column(Boolean, nullable=False, default=False)

    requirement = relationship("Requirement", back_populates="acceptance_criteria")


class UserStory(Base):
    __tablename__ = "user_stories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    story_id = Column(String(30), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    as_a = Column(String(100), nullable=False)
    i_want = Column(Text, nullable=False)
    so_that = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="draft")

    project = relationship("Project", back_populates="user_stories")
    trace_links = relationship(
        "TraceabilityLink", back_populates="user_story", cascade="all, delete-orphan", order_by="TraceabilityLink.id"
    )


class UseCase(Base):
    __tablename__ = "use_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    use_case_id = Column(String(30), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    actor = Column(String(100), nullable=False)
    goal = Column(Text, nullable=False)
    preconditions = Column(Text, nullable=True)
    main_flow = Column(Text, nullable=False)
    alternate_flows = Column(Text, nullable=True)
    postconditions = Column(Text, nullable=True)

    project = relationship("Project", back_populates="use_cases")
    trace_links = relationship(
        "TraceabilityLink", back_populates="use_case", cascade="all, delete-orphan", order_by="TraceabilityLink.id"
    )


class TraceabilityLink(Base):
    __tablename__ = "traceability_links"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_story_id = Column(Integer, ForeignKey("user_stories.id", ondelete="CASCADE"), nullable=True, index=True)
    use_case_id = Column(Integer, ForeignKey("use_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    coverage = Column(String(20), nullable=False, default="covered")
    notes = Column(Text, nullable=True)

    requirement = relationship("Requirement", back_populates="trace_links")
    user_story = relationship("UserStory", back_populates="trace_links")
    use_case = relationship("UseCase", back_populates="trace_links")
