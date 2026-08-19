"""Data quality validation for CSV-derived customer datasets.

Implements `DataQualityValidator` (`docs/ML_SPEC.md` §3): built once during
Phase 2 for dev-dataset ingestion and reused unchanged, via the same
`DataQualityValidator` class, for every company upload once that workflow is
built (`docs/PROJECT_SPEC.md` §16) — one code path, not duplicated logic.

Each check yields "pass" / "warn" / "fail". Per the ML_SPEC §3 table, a check
fails by default when its documented fail condition is met; the two checks
the table explicitly downgrades are `unexpected_columns` ("warn, not fail")
and, by the same "informational, not necessarily wrong" reasoning,
`high_cardinality` and `identifier_columns` (both flag a *likely* identifier
for human review, not a confirmed defect).

Output shape matches ML_SPEC §3 exactly:
`{ "checks": [...], "overall_status": "pass|warn|fail", "row_count": ...,
   "issues_found": ... }`.

Run directly against the combined development dataset:
`python -m ml.data_quality.validator`
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

STATUS_RANK = {"pass": 0, "warn": 1, "fail": 2}

# A required column with missing values below this share is a warning
# (recoverable via imputation); at or above it, the column is unreliable
# enough to fail (docs/ML_SPEC.md §3: "beyond an acceptable threshold").
MISSING_VALUE_FAIL_THRESHOLD = 0.05

# No real customer has 100 years of tenure; anything past this is an
# impossible value, not just an outlier (docs/ML_SPEC.md §3 example).
MAX_PLAUSIBLE_TENURE_MONTHS = 1200

# A column where more than this share of values are unique per row is very
# likely an identifier rather than a genuine category (docs/ML_SPEC.md §3).
HIGH_CARDINALITY_UNIQUE_RATIO = 0.9

IDENTIFIER_NAME_PATTERN = re.compile(r"(^id$|_id$|^id_|customerid|uuid|guid)", re.IGNORECASE)

# Columns conceptually numeric but historically prone to arriving as text in
# raw uploads (mirrors the real `Total Charges` issue, docs/PROJECT_SPEC.md
# §2.1) — checked for coercibility and impossible values.
NUMERIC_COLUMNS = ("Tenure Months", "Monthly Charges", "Total Charges")


class MalformedCSVError(Exception):
    """Raised when a file cannot be parsed into a DataFrame at all."""


def load_csv_safely(path: str | Path) -> pd.DataFrame:
    """Parse a CSV, converting parse-level failures into `MalformedCSVError`
    instead of letting pandas' raw exceptions propagate (docs/ML_SPEC.md §3:
    "Malformed CSV | Ragged rows, unparseable encoding")."""
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise MalformedCSVError(f"File is not valid UTF-8: {exc}") from exc
    except pd.errors.ParserError as exc:
        raise MalformedCSVError(f"CSV could not be parsed (ragged rows?): {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise MalformedCSVError(f"File has no parseable content: {exc}") from exc


@dataclass
class CheckResult:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


class DataQualityValidator:
    """Runs the full ML_SPEC §3 check suite against an in-memory DataFrame.

    `required_columns` is the schema contract to validate against (the dev
    pipeline passes `ml.config.MODELING_COLUMNS`; a company upload will pass
    whatever its confirmed column mapping resolves to, per PROJECT_SPEC
    §16.1 — the validator itself doesn't know or care which caller it is).
    `target_column` is optional: omit it for prediction-only uploads, where
    no historical outcome column is required or expected.
    """

    def __init__(
        self,
        required_columns: list[str],
        target_column: str | None = None,
        id_column: str | None = None,
    ) -> None:
        self.required_columns = required_columns
        self.target_column = target_column
        self.id_column = id_column

    def validate(self, df: pd.DataFrame) -> dict[str, Any]:
        checks: list[CheckResult] = [
            self._check_missing_required_columns(df),
            self._check_unexpected_columns(df),
            self._check_missing_values(df),
            self._check_duplicates(df),
            self._check_wrong_dtypes(df),
            self._check_invalid_values(df),
            self._check_inconsistent_categories(df),
            self._check_high_cardinality(df),
            self._check_identifier_columns(df),
        ]
        target_check = self._check_target(df)
        if target_check is not None:
            checks.append(target_check)

        overall_status = max((c.status for c in checks), key=lambda s: STATUS_RANK[s])
        issues_found = sum(1 for c in checks if c.status != "pass")

        return {
            "checks": [c.to_dict() for c in checks],
            "overall_status": overall_status,
            "row_count": int(df.shape[0]),
            "issues_found": issues_found,
        }

    # -- individual checks ---------------------------------------------

    def _check_missing_required_columns(self, df: pd.DataFrame) -> CheckResult:
        missing = [c for c in self.required_columns if c not in df.columns]
        return CheckResult(
            "missing_required_columns",
            "fail" if missing else "pass",
            {"missing_columns": missing},
        )

    def _check_unexpected_columns(self, df: pd.DataFrame) -> CheckResult:
        known = set(self.required_columns)
        if self.target_column:
            known.add(self.target_column)
        if self.id_column:
            known.add(self.id_column)
        extra = [c for c in df.columns if c not in known]
        return CheckResult(
            "unexpected_columns",
            "warn" if extra else "pass",
            {"unexpected_columns": extra},
        )

    def _check_missing_values(self, df: pd.DataFrame) -> CheckResult:
        present = [c for c in self.required_columns if c in df.columns]
        if not present:
            return CheckResult("missing_values", "pass", {"columns_with_missing_share": {}})

        blank_as_null = df[present].replace(r"^\s*$", pd.NA, regex=True)
        missing_share = blank_as_null.isna().mean()
        offenders = {col: round(float(share), 4) for col, share in missing_share.items() if share > 0}

        if not offenders:
            status = "pass"
        elif max(offenders.values()) >= MISSING_VALUE_FAIL_THRESHOLD:
            status = "fail"
        else:
            status = "warn"
        return CheckResult("missing_values", status, {"columns_with_missing_share": offenders})

    def _check_duplicates(self, df: pd.DataFrame) -> CheckResult:
        duplicate_rows = int(df.duplicated().sum())
        duplicate_ids = 0
        if self.id_column and self.id_column in df.columns:
            duplicate_ids = int(df[self.id_column].duplicated().sum())
        status = "fail" if (duplicate_rows or duplicate_ids) else "pass"
        return CheckResult(
            "duplicates",
            status,
            {"duplicate_rows": duplicate_rows, "duplicate_id_values": duplicate_ids},
        )

    def _check_wrong_dtypes(self, df: pd.DataFrame) -> CheckResult:
        offenders: dict[str, int] = {}
        for col in NUMERIC_COLUMNS:
            if col not in df.columns:
                continue
            non_null = df[col].replace(r"^\s*$", pd.NA, regex=True).dropna()
            if non_null.empty:
                continue
            failures = int(pd.to_numeric(non_null, errors="coerce").isna().sum())
            if failures:
                offenders[col] = failures
        return CheckResult(
            "wrong_dtypes",
            "fail" if offenders else "pass",
            {"non_coercible_value_counts": offenders},
        )

    def _check_invalid_values(self, df: pd.DataFrame) -> CheckResult:
        issues: dict[str, int] = {}

        if "Monthly Charges" in df.columns:
            vals = pd.to_numeric(df["Monthly Charges"], errors="coerce")
            n = int((vals < 0).sum())
            if n:
                issues["negative_monthly_charges"] = n

        if "Total Charges" in df.columns:
            vals = pd.to_numeric(df["Total Charges"], errors="coerce")
            n = int((vals < 0).sum())
            if n:
                issues["negative_total_charges"] = n

        if "Tenure Months" in df.columns:
            vals = pd.to_numeric(df["Tenure Months"], errors="coerce")
            n_negative = int((vals < 0).sum())
            if n_negative:
                issues["negative_tenure_months"] = n_negative
            n_implausible = int((vals > MAX_PLAUSIBLE_TENURE_MONTHS).sum())
            if n_implausible:
                issues["implausible_tenure_months"] = n_implausible

        return CheckResult("invalid_values", "fail" if issues else "pass", issues)

    def _check_inconsistent_categories(self, df: pd.DataFrame) -> CheckResult:
        offenders: dict[str, list[str]] = {}
        categorical_cols = [c for c in self.required_columns if c in df.columns and c not in NUMERIC_COLUMNS]
        for col in categorical_cols:
            raw_values = df[col].dropna().astype(str)
            raw_unique = set(raw_values.unique())
            normalized_unique = {v.strip().lower() for v in raw_unique}
            if len(normalized_unique) < len(raw_unique):
                offenders[col] = sorted(raw_unique)
        return CheckResult(
            "inconsistent_categories",
            "fail" if offenders else "pass",
            {"columns_with_case_or_whitespace_variants": offenders},
        )

    def _check_high_cardinality(self, df: pd.DataFrame) -> CheckResult:
        offenders: dict[str, float] = {}
        categorical_cols = [c for c in self.required_columns if c in df.columns and c not in NUMERIC_COLUMNS]
        for col in categorical_cols:
            n = df[col].shape[0]
            if n == 0:
                continue
            ratio = df[col].nunique(dropna=True) / n
            if ratio > HIGH_CARDINALITY_UNIQUE_RATIO:
                offenders[col] = round(float(ratio), 4)
        return CheckResult(
            "high_cardinality",
            "warn" if offenders else "pass",
            {"columns_unique_ratio": offenders},
        )

    def _check_identifier_columns(self, df: pd.DataFrame) -> CheckResult:
        # A caller-declared `id_column` is a known, handled identifier (see
        # the `duplicates` check) — this check exists to surface *undeclared*
        # identifier-like columns the caller hasn't accounted for.
        matches = [
            c
            for c in df.columns
            if c != self.id_column and IDENTIFIER_NAME_PATTERN.search(c.replace(" ", ""))
        ]
        return CheckResult(
            "identifier_columns",
            "warn" if matches else "pass",
            {"identifier_like_columns": matches},
        )

    def _check_target(self, df: pd.DataFrame) -> CheckResult | None:
        if self.target_column is None:
            return None
        if self.target_column not in df.columns:
            return CheckResult("target_column", "fail", {"reason": "missing"})

        values = df[self.target_column].dropna()
        unique_values = set(values.unique().tolist())

        if len(unique_values) < 2:
            return CheckResult(
                "target_column",
                "fail",
                {"reason": "single_class", "unique_values": [str(v) for v in unique_values]},
            )
        if not unique_values <= {0, 1, "0", "1"}:
            return CheckResult(
                "target_column",
                "fail",
                {"reason": "non_binary", "unique_values": sorted(str(v) for v in unique_values)},
            )
        return CheckResult("target_column", "pass", {"unique_values": sorted(str(v) for v in unique_values)})


def main() -> None:
    from ml.config import DATA_PROCESSED_DIR, MODELING_COLUMNS, TARGET_COLUMN

    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    validator = DataQualityValidator(
        required_columns=MODELING_COLUMNS,
        target_column=TARGET_COLUMN,
        id_column="CustomerID",
    )
    report = validator.validate(df)

    report_path = Path(__file__).resolve().parent / "combined_dataset_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Data quality report written to {report_path}")
    print(f"Overall status: {report['overall_status']} ({report['issues_found']} issue(s) found)")


if __name__ == "__main__":
    main()
