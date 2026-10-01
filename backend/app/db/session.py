"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    options: dict[str, object] = {"pool_pre_ping": True, "pool_recycle": 2800}
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}}
    database = create_engine(url, **options)
    if url.startswith("sqlite"):

        @event.listens_for(database, "connect")
        def _sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    if url.startswith("mysql"):

        @event.listens_for(database, "connect")
        def _mysql_utc(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("SET time_zone = '+00:00'")
            cursor.close()

    return database


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
