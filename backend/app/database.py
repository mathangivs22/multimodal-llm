"""Database engine, session factory and FastAPI dependency.

Works with MySQL (recommended via DATABASE_URL in .env) or SQLite as a fallback.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

_url = make_url(DATABASE_URL)
_is_sqlite = _url.get_backend_name() == "sqlite"

if _is_sqlite:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless this is on
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,   # reconnect if MySQL dropped an idle connection
        pool_recycle=3600,    # recycle before MySQL's wait_timeout closes it
    )


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401  (registers tables on Base)
    Base.metadata.create_all(bind=engine)
