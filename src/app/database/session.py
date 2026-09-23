from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _database_url():
    url = make_url(settings.DATABASE_URL)
    # psycopg v3 is the supported PostgreSQL driver in the production stack.
    if url.get_backend_name() == "postgresql" and url.get_driver_name() in {None, ""}:
        url = url.set(drivername="postgresql+psycopg")
    return url


url = _database_url()
engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
    "pool_pre_ping": True,
    "pool_recycle": settings.DATABASE_POOL_RECYCLE,
}
if url.get_backend_name() != "sqlite":
    engine_kwargs.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    )
else:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(url, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
