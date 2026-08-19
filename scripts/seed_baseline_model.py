"""One-off script: seeds the shared baseline model's `models` row.

`docs/DATABASE_SPEC.md` §2.7 pins this exact step to this phase: "the
initial baseline model ... is produced by the Phase 1-7 ML pipeline and
seeded into this table via a one-off script during Phase 9 (Database &
Authentication) ... no `training_jobs` row is created for it."
`docs/DEPLOYMENT.md` §5.3 confirms the same for first deploy.

Run once, after `alembic upgrade head` has created the schema:

    python scripts/seed_baseline_model.py

Idempotent: if a `models` row already exists for the discovered artifact's
`artifact_path`, the script reports that and exits without inserting a
duplicate (safe to re-run, e.g. after a redeploy).

KNOWN SCHEMA LIMITATION (documented, not silently worked around): the
baseline model is actually trained on the *combined* development dataset —
IBM benchmark + synthetic Pakistan + synthetic India
(`docs/PROJECT_SPEC.md` §3.1) — but `models.trained_on_dataset_id` is a
single FK to one `datasets` row, and `datasets.source_type`'s CHECK
constraint (`docs/DATABASE_SPEC.md` §2.5) has no "combined" value. This
script seeds one representative `datasets` row (`source_type =
'dev_benchmark_ibm'`) standing in for the combined dataset, with
`original_filename` set to the actual combined-dataset filename recorded in
the model's own metadata so the real provenance is still visible on that
row. This is a modeling gap in the schema as specified, not an attempt to
misrepresent the data — flagged here and in the Phase 8 report rather than
silently choosing a source_type that looks more "correct" than the schema
allows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ml import config as ml_config  # noqa: E402

from backend.db.models import Dataset, Model  # noqa: E402
from backend.db.session import build_engine, default_database_url  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
import os  # noqa: E402


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_recommended_model_dir() -> Path:
    artifacts_dir = ml_config.ARTIFACTS_DIR
    for child in sorted(artifacts_dir.iterdir()):
        metadata_path = child / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = _read_json(metadata_path)
        if metadata.get("selected_as_recommended_production_model"):
            return child
    raise SystemExit(
        f"No model artifact under {artifacts_dir} has "
        "selected_as_recommended_production_model=true. Train and select a "
        "production model (Phase 5-7) before seeding."
    )


def main() -> None:
    model_dir = _find_recommended_model_dir()
    metadata = _read_json(model_dir / "metadata.json")
    metrics_path = model_dir / "metrics.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}

    artifact_path = str(model_dir.relative_to(REPO_ROOT)).replace("\\", "/")

    database_url = os.environ.get("DATABASE_URL", default_database_url())
    engine = build_engine(database_url)
    Session = sessionmaker(bind=engine, future=True)

    with Session() as db:
        existing = db.query(Model).filter(Model.artifact_path == artifact_path).one_or_none()
        if existing is not None:
            print(
                f"Baseline model already seeded: models.id={existing.id} "
                f"artifact_path={artifact_path!r}. Nothing to do."
            )
            return

        trained_on_filename = metadata.get("trained_on_dataset", "combined_development_dataset.csv")
        dataset = Dataset(
            organization_id=None,
            original_filename=trained_on_filename,
            storage_path=f"{artifact_path}/__seeded_dev_dataset__",
            source_type="dev_benchmark_ibm",
            row_count=int(metadata.get("train_row_count", 0)),
            column_schema=metadata.get("feature_schema", []),
            column_mapping=None,
            data_quality_report={
                "note": (
                    "Seeded at Phase 8 for baseline model provenance/FK purposes, not "
                    "computed by DataQualityValidator at seed time. The real Phase 2 "
                    "quality report for this pipeline run lives in ml/eda/ output, not "
                    "in this JSON column."
                ),
                "checks": [],
            },
            has_target_column=True,
            target_column_name="Churn Value",
            uploaded_by_user_id=None,
        )
        db.add(dataset)
        db.flush()

        model = Model(
            organization_id=None,
            model_type="baseline_global",
            algorithm=metadata["algorithm"],
            version=int(metadata.get("version", 1)),
            artifact_path=artifact_path,
            feature_schema=metadata.get("feature_schema", []),
            metrics=metrics,
            decision_threshold=float(metadata["decision_threshold"]),
            risk_thresholds=metadata.get("risk_thresholds", {"low_max": 0.3, "medium_max": 0.6}),
            trained_on_dataset_id=dataset.id,
            training_job_id=None,
            is_active=True,
        )
        db.add(model)
        db.commit()

        print(
            f"Seeded baseline model: models.id={model.id} algorithm={model.algorithm!r} "
            f"artifact_path={artifact_path!r} trained_on_dataset_id={dataset.id}"
        )


if __name__ == "__main__":
    main()
