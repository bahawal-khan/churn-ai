"""Shared SQLAlchemy declarative base (`docs/DATABASE_SPEC.md`)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
