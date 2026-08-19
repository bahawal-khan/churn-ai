"""Engine/session construction (`docs/DATABASE_SPEC.md` §7).

`PRAGMA foreign_keys = ON` is set on every SQLite connection here — SQLite
defaults this off, and without it every FK constraint in `models.py` would
be silently unenforced.

Schema creation itself is never done here (no `create_all()` at runtime):
per `skills.md` ("track schema changes via migrations, not manual edits"),
the schema is always brought up via `alembic upgrade head`
(`backend/db/migrations/`). This module only opens connections/sessions
against whatever schema already exists at `DATABASE_URL`.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, g
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent / "churnai.db"


def default_database_url() -> str:
    return f"sqlite:///{_DEFAULT_SQLITE_PATH}"


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_app(app: Flask) -> None:
    """Builds one engine/sessionmaker per app and opens/closes one `Session`
    per request via `g` — the standard Flask-SQLAlchemy-free pattern, kept
    dependency-light since only `db/` needs SQLAlchemy access."""
    database_url = app.config.get("DATABASE_URL") or os.environ.get(
        "DATABASE_URL", default_database_url()
    )
    engine = build_engine(database_url)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = session_factory

    @app.teardown_appcontext
    def _remove_session(_exception: BaseException | None) -> None:
        session: Session | None = g.pop("db_session", None)
        if session is not None:
            session.close()


def get_session() -> Session:
    """Returns the current request's `Session`, opening one on first use."""
    from flask import current_app

    if "db_session" not in g:
        factory = current_app.extensions["db_session_factory"]
        g.db_session = factory()
    return g.db_session
