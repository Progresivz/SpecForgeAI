from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class PrototypeDesign(Base):
    __tablename__ = 'prototype_designs'
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    style_notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    project = relationship('Project', back_populates='prototype_design')
    screens = relationship('PrototypeScreen', back_populates='design', cascade='all, delete-orphan', order_by='PrototypeScreen.position')
    flows = relationship('PrototypeFlow', back_populates='design', cascade='all, delete-orphan', order_by='PrototypeFlow.id')

class PrototypeScreen(Base):
    __tablename__ = 'prototype_screens'
    id: Mapped[int] = mapped_column(primary_key=True)
    design_id: Mapped[int] = mapped_column(ForeignKey('prototype_designs.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    route: Mapped[str] = mapped_column(String(200), nullable=False, default='/')
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default='')
    layout: Mapped[str] = mapped_column(String(100), nullable=False, default='standard')
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    design = relationship('PrototypeDesign', back_populates='screens')
    components = relationship('PrototypeComponent', back_populates='screen', cascade='all, delete-orphan', order_by='PrototypeComponent.position')

class PrototypeComponent(Base):
    __tablename__ = 'prototype_components'
    id: Mapped[int] = mapped_column(primary_key=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey('prototype_screens.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    interaction: Mapped[str] = mapped_column(Text, nullable=False, default='')
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    screen = relationship('PrototypeScreen', back_populates='components')

class PrototypeFlow(Base):
    __tablename__ = 'prototype_flows'
    id: Mapped[int] = mapped_column(primary_key=True)
    design_id: Mapped[int] = mapped_column(ForeignKey('prototype_designs.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    from_screen: Mapped[str] = mapped_column(String(150), nullable=False)
    to_screen: Mapped[str] = mapped_column(String(150), nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default='')
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    design = relationship('PrototypeDesign', back_populates='flows')
