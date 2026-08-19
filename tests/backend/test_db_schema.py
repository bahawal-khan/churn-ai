"""Verifies `docs/DATABASE_SPEC.md` §3 (FK on-delete behaviors), §5 (CHECK/
UNIQUE constraints), and the `training_jobs` <-> `models` circular FK —
against the real Alembic-migrated schema (`test_db_url` fixture), not just
the ORM's in-memory model definitions. Pure DB-layer tests: no Flask app,
no HTTP.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.db.models import (
    AuditLog,
    Customer,
    Dataset,
    Explanation,
    Model,
    Organization,
    PasswordResetToken,
    Prediction,
)
from backend.db.models import Session as SessionRecord
from backend.db.models import TrainingJob, User
from backend.db.session import build_engine


@pytest.fixture()
def db(test_db_url):
    engine = build_engine(test_db_url)
    factory = sessionmaker(bind=engine, future=True)
    session = factory()
    yield session
    session.close()


def _make_org(db, name="Acme"):
    org = Organization(name=name)
    db.add(org)
    db.flush()
    return org


def _make_user(db, org, email="user@example.com"):
    user = User(email=email, password_hash="x", full_name="Test User", organization_id=org.id)
    db.add(user)
    db.flush()
    return user


def _make_dataset(db, org=None, source_type="dev_benchmark_ibm"):
    dataset = Dataset(
        organization_id=org.id if org else None,
        original_filename="data.csv",
        storage_path=f"path-{id(object())}",
        source_type=source_type,
        row_count=10,
        column_schema=[],
        data_quality_report={"checks": []},
    )
    db.add(dataset)
    db.flush()
    return dataset


def _make_model(db, dataset, org=None):
    model = Model(
        organization_id=org.id if org else None,
        model_type="baseline_global" if org is None else "company_specific",
        algorithm="random_forest",
        version=1,
        artifact_path=f"artifact-{id(object())}",
        feature_schema=[],
        metrics={},
        decision_threshold=0.5,
        risk_thresholds={"low_max": 0.3, "medium_max": 0.6},
        trained_on_dataset_id=dataset.id,
    )
    db.add(model)
    db.flush()
    return model


# ---------------------------------------------------------------------------
# FK enforcement is on at all (PRAGMA foreign_keys)
# ---------------------------------------------------------------------------


def test_foreign_keys_are_enforced_at_all(db):
    db.add(SessionRecord(id="orphan", user_id=999999, expires_at=datetime.utcnow()))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# ---------------------------------------------------------------------------
# CASCADE
# ---------------------------------------------------------------------------


def test_deleting_user_cascades_sessions(db):
    org = _make_org(db)
    user = _make_user(db, org)
    db.add(SessionRecord(id="s1", user_id=user.id, expires_at=datetime.utcnow()))
    db.commit()

    db.delete(user)
    db.commit()

    assert db.get(SessionRecord, "s1") is None


def test_deleting_user_cascades_password_reset_tokens(db):
    org = _make_org(db)
    user = _make_user(db, org)
    token = PasswordResetToken(
        user_id=user.id, token_hash="h", expires_at=datetime.utcnow()
    )
    db.add(token)
    db.commit()
    token_id = token.id

    db.delete(user)
    db.commit()

    assert db.get(PasswordResetToken, token_id) is None


def test_deleting_organization_cascades_datasets_and_customers(db):
    org = _make_org(db)
    dataset = _make_dataset(db, org=org, source_type="company_upload")
    customer = Customer(organization_id=org.id, dataset_id=dataset.id, feature_data={})
    db.add(customer)
    db.commit()
    dataset_id, customer_id = dataset.id, customer.id

    db.delete(org)
    db.commit()

    assert db.get(Dataset, dataset_id) is None
    assert db.get(Customer, customer_id) is None


def test_deleting_prediction_cascades_explanation(db):
    org = _make_org(db)
    dataset = _make_dataset(db)
    model = _make_model(db, dataset)
    prediction = Prediction(
        organization_id=org.id,
        model_id=model.id,
        prediction_type="single",
        input_data={},
        churn_probability=0.5,
        predicted_class=True,
        risk_level="medium",
    )
    db.add(prediction)
    db.flush()
    explanation = Explanation(
        prediction_id=prediction.id, shap_values={}, base_value=0.1, top_factors=[]
    )
    db.add(explanation)
    db.commit()
    explanation_id = explanation.id

    db.delete(prediction)
    db.commit()

    assert db.get(Explanation, explanation_id) is None


# ---------------------------------------------------------------------------
# RESTRICT
# ---------------------------------------------------------------------------


def test_deleting_dataset_referenced_by_model_is_restricted(db):
    dataset = _make_dataset(db)
    _make_model(db, dataset)
    db.commit()

    db.delete(dataset)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_model_referenced_by_prediction_is_restricted(db):
    org = _make_org(db)
    dataset = _make_dataset(db)
    model = _make_model(db, dataset)
    db.add(
        Prediction(
            organization_id=org.id,
            model_id=model.id,
            prediction_type="single",
            input_data={},
            churn_probability=0.5,
            predicted_class=False,
            risk_level="low",
        )
    )
    db.commit()

    db.delete(model)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_organization_with_a_user_is_restricted(db):
    org = _make_org(db)
    _make_user(db, org)
    db.commit()

    db.delete(org)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------------------
# SET NULL
# ---------------------------------------------------------------------------


def test_deleting_customer_sets_prediction_customer_id_null(db):
    org = _make_org(db)
    dataset = _make_dataset(db, org=org, source_type="company_upload")
    model = _make_model(db, dataset)
    customer = Customer(organization_id=org.id, dataset_id=dataset.id, feature_data={})
    db.add(customer)
    db.flush()
    prediction = Prediction(
        organization_id=org.id,
        model_id=model.id,
        prediction_type="batch",
        customer_id=customer.id,
        input_data={},
        churn_probability=0.2,
        predicted_class=False,
        risk_level="low",
    )
    db.add(prediction)
    db.commit()
    prediction_id = prediction.id

    db.delete(customer)
    db.commit()

    refreshed = db.get(Prediction, prediction_id)
    assert refreshed is not None
    assert refreshed.customer_id is None


def test_deleting_user_sets_dataset_uploaded_by_null(db):
    org = _make_org(db)
    user = _make_user(db, org)
    dataset = Dataset(
        organization_id=org.id,
        original_filename="f.csv",
        storage_path="p1",
        source_type="company_upload",
        row_count=1,
        column_schema=[],
        data_quality_report={},
        uploaded_by_user_id=user.id,
    )
    db.add(dataset)
    db.commit()
    dataset_id = dataset.id

    db.delete(user)
    db.commit()

    refreshed = db.get(Dataset, dataset_id)
    assert refreshed is not None
    assert refreshed.uploaded_by_user_id is None


def test_deleting_organization_sets_audit_log_organization_null(db):
    # No `users` row references this org, so (unlike the RESTRICT test
    # above) the delete succeeds and SET NULL applies to the audit log.
    org = _make_org(db)
    log = AuditLog(organization_id=org.id, user_id=None, event_type="login")
    db.add(log)
    db.commit()
    log_id = log.id

    db.delete(org)
    db.commit()

    refreshed = db.get(AuditLog, log_id)
    assert refreshed is not None
    assert refreshed.organization_id is None


# ---------------------------------------------------------------------------
# The circular models <-> training_jobs FK (`docs/DATABASE_SPEC.md` §3)
# ---------------------------------------------------------------------------


def test_training_job_and_model_circular_reference_both_directions(db):
    org = _make_org(db)
    dataset = _make_dataset(db, org=org, source_type="company_upload")

    job = TrainingJob(organization_id=org.id, dataset_id=dataset.id, status="queued")
    db.add(job)
    db.flush()

    model = Model(
        organization_id=org.id,
        model_type="company_specific",
        algorithm="gradient_boosting",
        version=1,
        artifact_path="circular-artifact",
        feature_schema=[],
        metrics={},
        decision_threshold=0.5,
        risk_thresholds={"low_max": 0.3, "medium_max": 0.6},
        trained_on_dataset_id=dataset.id,
        training_job_id=job.id,
    )
    db.add(model)
    db.flush()

    job.resulting_model_id = model.id
    job.status = "completed"
    db.commit()

    assert db.get(TrainingJob, job.id).resulting_model_id == model.id
    assert db.get(Model, model.id).training_job_id == job.id

    # Deleting the model SET NULLs the job's back-reference (ondelete=SET NULL).
    model_id = model.id
    db.delete(model)
    db.commit()
    assert db.get(TrainingJob, job.id).resulting_model_id is None
    assert db.get(Model, model_id) is None


# ---------------------------------------------------------------------------
# CHECK constraints
# ---------------------------------------------------------------------------


def test_invalid_source_type_rejected_by_check_constraint(db):
    db.add(
        Dataset(
            organization_id=None,
            original_filename="f.csv",
            storage_path="bad-source-type",
            source_type="not_a_real_source",
            row_count=1,
            column_schema=[],
            data_quality_report={},
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_invalid_risk_level_rejected_by_check_constraint(db):
    org = _make_org(db)
    dataset = _make_dataset(db)
    model = _make_model(db, dataset)
    db.add(
        Prediction(
            organization_id=org.id,
            model_id=model.id,
            prediction_type="single",
            input_data={},
            churn_probability=0.5,
            predicted_class=True,
            risk_level="extreme",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_churn_probability_out_of_range_rejected(db):
    org = _make_org(db)
    dataset = _make_dataset(db)
    model = _make_model(db, dataset)
    db.add(
        Prediction(
            organization_id=org.id,
            model_id=model.id,
            prediction_type="single",
            input_data={},
            churn_probability=1.5,
            predicted_class=True,
            risk_level="high",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_invalid_theme_preference_rejected(db):
    org = _make_org(db)
    db.add(
        User(
            email="bad-theme@example.com",
            password_hash="x",
            full_name="X",
            organization_id=org.id,
            theme_preference="rainbow",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------------------
# UNIQUE constraints
# ---------------------------------------------------------------------------


def test_duplicate_user_email_rejected(db):
    org = _make_org(db)
    _make_user(db, org, email="dup@example.com")
    db.commit()

    db.add(User(email="dup@example.com", password_hash="x", full_name="Y", organization_id=org.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_model_artifact_path_rejected(db):
    dataset = _make_dataset(db)
    _make_model(db, dataset)
    db.commit()

    db.add(
        Model(
            organization_id=None,
            model_type="baseline_global",
            algorithm="logistic_regression",
            version=2,
            artifact_path=db.query(Model).first().artifact_path,
            feature_schema=[],
            metrics={},
            decision_threshold=0.5,
            risk_thresholds={"low_max": 0.3, "medium_max": 0.6},
            trained_on_dataset_id=dataset.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_explanation_per_prediction_rejected(db):
    org = _make_org(db)
    dataset = _make_dataset(db)
    model = _make_model(db, dataset)
    prediction = Prediction(
        organization_id=org.id,
        model_id=model.id,
        prediction_type="single",
        input_data={},
        churn_probability=0.4,
        predicted_class=False,
        risk_level="medium",
    )
    db.add(prediction)
    db.flush()
    db.add(Explanation(prediction_id=prediction.id, shap_values={}, base_value=0.1, top_factors=[]))
    db.commit()

    db.add(Explanation(prediction_id=prediction.id, shap_values={}, base_value=0.2, top_factors=[]))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
