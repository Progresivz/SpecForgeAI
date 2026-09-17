from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import session as database_session


def get_db() -> Generator[Session, None, None]:
    db = database_session.SessionLocal()

    try:
        yield db
    finally:
        db.close()
