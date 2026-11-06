from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Engine | None = None) -> None:
    """Create tables and the append-only protection on the audit table.

    For v1 tables are created from the models. Switch to Alembic migrations
    before the first 'validated' release so schema changes are under change control.
    """
    from app import models  # noqa: F401  (registers models)
    from app.models.audit_event import install_append_only_guard
    from app.models.esignature import install_esignature_guard

    bind = bind or engine
    Base.metadata.create_all(bind)
    install_append_only_guard(bind)
    install_esignature_guard(bind)
