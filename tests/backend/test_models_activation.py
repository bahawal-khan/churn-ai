"""`POST /api/models/:id/(activate|deactivate)` (`docs/API.md`,
`docs/DATABASE_SPEC.md` §2.7's "at most one active company model per org"
rule). Company-specific `models` DB rows are inserted directly here (not via
a full training run, which `tests/backend/test_training.py` already
exercises end-to-end) to keep these ownership/exclusivity checks fast.
"""

from __future__ import annotations

from backend.db.models import Model, User


def _current_org_id(app, email="test.user@example.com"):
    with app.app_context():
        from backend.db import session as db_session

        db = db_session.get_session()
        user = db.query(User).filter(User.email == email).one()
        return user.organization_id


def _insert_company_model(app, *, organization_id: int, is_active: bool = False) -> int:
    with app.app_context():
        from backend.db import session as db_session

        db = db_session.get_session()
        model = Model(
            organization_id=organization_id,
            model_type="company_specific",
            algorithm="random_forest",
            version=1,
            artifact_path=f"/nonexistent/artifact/{organization_id}/{is_active}",
            feature_schema=[{"name": "Tenure Months", "dtype": "numeric"}],
            metrics={"validation": {}, "test": {}},
            decision_threshold=0.5,
            risk_thresholds={"low_max": 0.3, "medium_max": 0.6},
            trained_on_dataset_id=_seed_dataset(db, organization_id),
            training_job_id=None,
            is_active=is_active,
        )
        db.add(model)
        db.commit()
        return model.id


def _seed_dataset(db, organization_id: int) -> int:
    from backend.db.models import Dataset

    dataset = Dataset(
        organization_id=organization_id,
        original_filename="test.csv",
        storage_path=f"/tmp/test-{organization_id}-{id(db)}.csv",
        source_type="company_upload",
        row_count=1,
        column_schema=[],
        data_quality_report={"checks": []},
        has_target_column=True,
        target_column_name="Churn Value",
    )
    db.add(dataset)
    db.flush()
    return dataset.id


def test_activate_unknown_model_returns_404(client):
    resp = client.post("/api/models/999999/activate")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_activating_a_model_deactivates_the_previous_one(client, app):
    org_id = _current_org_id(app)
    first_id = _insert_company_model(app, organization_id=org_id, is_active=True)
    second_id = _insert_company_model(app, organization_id=org_id, is_active=False)

    resp = client.post(f"/api/models/{second_id}/activate")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is True

    with app.app_context():
        from backend.db import session as db_session

        db = db_session.get_session()
        assert db.get(Model, second_id).is_active is True
        assert db.get(Model, first_id).is_active is False


def test_deactivate_model(client, app):
    org_id = _current_org_id(app)
    model_id = _insert_company_model(app, organization_id=org_id, is_active=True)

    resp = client.post(f"/api/models/{model_id}/deactivate")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is False


def test_cross_tenant_cannot_activate_others_model(client, second_client, app):
    org_id = _current_org_id(app)
    model_id = _insert_company_model(app, organization_id=org_id, is_active=False)

    resp = second_client.post(f"/api/models/{model_id}/activate")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"
