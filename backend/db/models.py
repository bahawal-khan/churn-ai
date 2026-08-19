"""SQLAlchemy ORM models for every table in `docs/DATABASE_SPEC.md` §2.

Column types, constraints (`NOT NULL`, `UNIQUE`, `CHECK`), foreign keys, and
indexes mirror that document exactly — this file is not the source of truth,
`DATABASE_SPEC.md` is; this is its SQLAlchemy expression. FK `ondelete`
behaviors match §3's table. `PRAGMA foreign_keys = ON` (required for SQLite
to enforce any of this) is set per-connection in `backend/db/session.py`,
never here.

Tables are declared in an order where every forward FK reference (e.g.
`training_jobs.resulting_model_id -> models.id`, declared before `models` is
defined) is valid: SQLite does not require the referenced table to exist at
`CREATE TABLE` time, only at DML/enforcement time, so the `training_jobs`
<-> `models` circular reference (`DATABASE_SPEC.md` §3) needs no
`use_alter`/deferred-constraint workaround.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


def _utcnow() -> datetime:
    # Naive UTC, not `datetime.now(timezone.utc)`: SQLAlchemy's SQLite
    # `DateTime` type round-trips a tz-aware value by storing it fine but
    # always reading it back naive (tzinfo silently dropped) — mixing naive
    # and aware datetimes then raises on comparison. Every datetime in this
    # schema is UTC by convention instead, consistently naive end to end.
    return datetime.utcnow()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("theme_preference IN ('light', 'dark')", name="ck_users_theme_preference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    theme_preference: Mapped[str] = mapped_column(Text, nullable=False, default="dark")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )


class Session(Base):
    """Backs the cookie-based session mechanism (`docs/BACKEND_SPEC.md` §4)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('dev_benchmark_ibm', 'dev_synthetic_pakistan', "
            "'dev_synthetic_india', 'company_upload')",
            name="ck_datasets_source_type",
        ),
        Index("ix_datasets_organization_id", "organization_id"),
        Index("ix_datasets_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_schema: Mapped[Any] = mapped_column(JSON, nullable=False)
    column_mapping: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    data_quality_report: Mapped[Any] = mapped_column(JSON, nullable=False)
    has_target_column: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_column_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_organization_id", "organization_id"),
        Index("ix_customers_dataset_id", "dataset_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    external_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    actual_churn_label: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class TrainingJob(Base):
    """State machine backing company-specific training (`docs/PROJECT_SPEC.md`
    §16, `docs/BACKEND_SPEC.md` §3). Declared before `Model` even though
    `resulting_model_id` forward-references `models.id` — see module
    docstring."""

    __tablename__ = "training_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'validating', 'preprocessing', 'training', "
            "'evaluating', 'completed', 'failed')",
            name="ck_training_jobs_status",
        ),
        Index("ix_training_jobs_organization_id", "organization_id"),
        Index("ix_training_jobs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_model_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("models.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Model(Base):
    """Every trained model version: shared baseline + company-specific
    versions (`docs/DATABASE_SPEC.md` §2.7). The "at most one active
    company-specific model per org" rule is an application-level constraint
    (§5), not a DB constraint, per that section's SQLite partial-unique-index
    limitation note."""

    __tablename__ = "models"
    __table_args__ = (
        CheckConstraint(
            "model_type IN ('baseline_global', 'company_specific')", name="ck_models_model_type"
        ),
        CheckConstraint(
            "algorithm IN ('logistic_regression', 'random_forest', 'gradient_boosting', 'ann')",
            name="ck_models_algorithm",
        ),
        Index("ix_models_organization_id", "organization_id"),
        Index("ix_models_created_at", "created_at"),
        Index("ix_models_org_type_active", "organization_id", "model_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    model_type: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    feature_schema: Mapped[Any] = mapped_column(JSON, nullable=False)
    metrics: Mapped[Any] = mapped_column(JSON, nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    risk_thresholds: Mapped[Any] = mapped_column(JSON, nullable=False)
    trained_on_dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    training_job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("training_jobs.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("prediction_type IN ('single', 'batch')", name="ck_predictions_type"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_predictions_risk_level"),
        CheckConstraint(
            "churn_probability >= 0 AND churn_probability <= 1",
            name="ck_predictions_probability_range",
        ),
        Index("ix_predictions_organization_id", "organization_id"),
        Index("ix_predictions_model_id", "model_id"),
        Index("ix_predictions_customer_id", "customer_id"),
        Index("ix_predictions_batch_job_id", "batch_job_id"),
        Index("ix_predictions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.id", ondelete="RESTRICT"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    input_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    churn_probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_class: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    batch_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Explanation(Base):
    __tablename__ = "explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    shap_values: Mapped[Any] = mapped_column(JSON, nullable=False)
    base_value: Mapped[float] = mapped_column(Float, nullable=False)
    top_factors: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('login', 'logout', 'signup', 'password_reset', 'dataset_upload', "
            "'dataset_delete', 'training_started', 'training_completed', 'training_failed', "
            "'model_activated', 'model_deactivated', 'prediction_made')",
            name="ck_audit_logs_event_type",
        ),
        Index("ix_audit_logs_organization_id", "organization_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_details: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
