"""Initial SpecForge schema baseline.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.database.base import Base
import app.database.init_db  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The baseline intentionally delegates table creation to SQLAlchemy metadata.
    # Future revisions should use explicit Alembic operations/autogenerate.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
