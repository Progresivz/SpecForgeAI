from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.database.base import Base
from app.database import session as database_session

from app.models.milestone import Milestone  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.requirement import (
    AcceptanceCriterion,
    Requirement,
    TraceabilityLink,
    UseCase,
    UserStory,
)  # noqa: F401
from app.models.prototype import (
    PrototypeDesign,
    PrototypeScreen,
    PrototypeComponent,
    PrototypeFlow,
)  # noqa: F401
from app.models.database_design import (
    DatabaseColumn,
    DatabaseDesign,
    DatabaseRelationship,
    DatabaseTable,
)  # noqa: F401
from app.models.documentation import (
    DocumentationDocument,
    DocumentationSet,
)  # noqa: F401
from app.models.git_repository import GitRepository  # noqa: F401
from app.models.maintenance import MaintenanceItem  # noqa: F401
from app.models.deadline import Deadline  # noqa: F401
from app.models.knowledge import KnowledgeEntry  # noqa: F401
from app.models.ai_artifact import AIArtifact  # noqa: F401
from app.models.task import DevelopmentTask  # noqa: F401
from app.models.workflow import (
    EngineeringFinding,
    GeneratedTest,
    EngineeringActivity,
)  # noqa: F401
from app.models.release import SDLCTtraceLink, Release  # noqa: F401
from app.models.release_automation import ReleaseAutomationRun  # noqa: F401
from app.models.copilot_conversation import (
    CopilotConversation,
    CopilotMessage,
)  # noqa: F401
from app.models.operations import OperationalJob, BackupRecord  # noqa: F401


def create_tables():
    engine = database_session.engine
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compat_migrations(engine)
    _record_schema_version(engine)


def _record_schema_version(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_version "
                "(version INTEGER NOT NULL, applied_at VARCHAR(40) NOT NULL)"
            )
        )
        current = conn.execute(
            text("SELECT MAX(version) FROM schema_version")
        ).scalar()

        if current is None:
            conn.execute(
                text(
                    "INSERT INTO schema_version(version, applied_at) "
                    "VALUES (:version, :applied_at)"
                ),
                {
                    "version": 1,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                },
            )


def _apply_sqlite_compat_migrations(engine):
    """Legacy SQLite compatibility; Alembic is authoritative in production."""
    if not engine.url.drivername.startswith("sqlite"):
        return

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "users" in tables:
        user_columns = {
            column["name"]
            for column in inspector.get_columns("users")
        }

        if "password" not in user_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN password VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )

    inspector = inspect(engine)

    if "projects" in inspector.get_table_names():
        project_columns = {
            column["name"]
            for column in inspector.get_columns("projects")
        }

        if "owner_id" not in project_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE projects "
                        "ADD COLUMN owner_id INTEGER"
                    )
                )


if __name__ == "__main__":
    create_tables()
    print("Database tables created")
