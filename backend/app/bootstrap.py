"""Database preparation at startup (schema, append-only guards, demo data).

The API and the worker start at the same time and both prepare the database. Without coordination
they race: both try to create new tables, and both insert the same new demo rows, and one of them
crashes on a unique-constraint violation. A PostgreSQL advisory lock makes the preparation run in
one process at a time; the second process then finds everything in place and changes nothing.
"""
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import settings
from app.database import SessionLocal, engine, init_db

_STARTUP_LOCK_KEY = 815_002  # distinct from the audit-trail writer lock


@contextmanager
def startup_lock(bind: Engine):
    """Hold a session-level advisory lock for the duration of the block (no-op on SQLite)."""
    if bind.dialect.name != "postgresql":
        yield
        return
    with bind.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _STARTUP_LOCK_KEY})
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _STARTUP_LOCK_KEY})


def prepare_database(bind: Engine | None = None) -> None:
    from app.seed import seed
    from app.services.knowledge_index import index_documents

    bind = bind or engine
    with startup_lock(bind):
        init_db(bind)
        with SessionLocal(bind=bind) as db:
            if settings.seed_demo_data:
                seed(db)
            index_documents(db)  # controlled documents for the Knowledge Assistant (not demo data)
