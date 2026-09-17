from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class DatabaseDesign(Base):
    __tablename__ = "database_designs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False, default="Primary Database Design")
    target_dialect = Column(String(30), nullable=False, default="postgresql")
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="database_design")
    tables = relationship("DatabaseTable", back_populates="design", cascade="all, delete-orphan", order_by="DatabaseTable.id")
    relationships = relationship("DatabaseRelationship", back_populates="design", cascade="all, delete-orphan", order_by="DatabaseRelationship.id")


class DatabaseTable(Base):
    __tablename__ = "database_tables"

    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(Integer, ForeignKey("database_designs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    design = relationship("DatabaseDesign", back_populates="tables")
    columns = relationship("DatabaseColumn", back_populates="table", cascade="all, delete-orphan", order_by="DatabaseColumn.position")


class DatabaseColumn(Base):
    __tablename__ = "database_columns"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("database_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False, default=1)
    nullable = Column(Boolean, nullable=False, default=True)
    primary_key = Column(Boolean, nullable=False, default=False)
    unique = Column(Boolean, nullable=False, default=False)
    default_value = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    table = relationship("DatabaseTable", back_populates="columns")


class DatabaseRelationship(Base):
    __tablename__ = "database_relationships"

    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(Integer, ForeignKey("database_designs.id", ondelete="CASCADE"), nullable=False, index=True)
    from_table = Column(String(100), nullable=False)
    from_column = Column(String(100), nullable=False)
    to_table = Column(String(100), nullable=False)
    to_column = Column(String(100), nullable=False)
    cardinality = Column(String(20), nullable=False, default="many-to-one")
    on_delete = Column(String(20), nullable=False, default="CASCADE")
    notes = Column(Text, nullable=True)

    design = relationship("DatabaseDesign", back_populates="relationships")
