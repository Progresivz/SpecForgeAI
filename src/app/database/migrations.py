import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Apply Alembic migrations from the application root."""
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    # Percent signs in URLs are interpolation-sensitive in Alembic Config.
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))
    logger.info("Running Alembic migrations")
    command.upgrade(config, "head")
