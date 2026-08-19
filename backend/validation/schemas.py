"""Pydantic request-envelope schemas (`docs/BACKEND_SPEC.md` §5: "every route
with a request body ... validates it against a Pydantic model before calling
its service"). These validate request *shape* only — the ML feature values
inside `customer_data` are dynamic per active model and are validated
separately against that model's `feature_schema`
(`backend/validation/feature_validation.py`), since no static Pydantic model
can know a schema that changes with which model is active.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Deliberately a hand-written regex, not `pydantic.EmailStr`: that type
# requires the optional `email-validator` dependency, and `CLAUDE.md`/
# `skills.md` forbid adding packages before the phase that needs them — a
# simple format check is all `docs/BACKEND_SPEC.md` §4 asks for ("valid
# format"), uniqueness is enforced separately at the service/DB layer.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# `docs/BACKEND_SPEC.md` §4: min 8 chars, >=1 upper, >=1 lower, >=1 digit,
# >=1 special character.
_PASSWORD_MIN_LENGTH = 8
_PASSWORD_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")


class SinglePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    customer_data: dict[str, Any]
    customer_id: str | None = None


def _validate_email_format(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _validate_password_policy(value: str) -> str:
    if len(value) < _PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {_PASSWORD_MIN_LENGTH} characters.")
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one number.")
    if not _PASSWORD_SPECIAL_RE.search(value):
        raise ValueError("Password must contain at least one special character.")
    return value


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str
    password: str
    confirm_password: str
    full_name: str

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return _validate_email_format(value)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return _validate_password_policy(value)

    @field_validator("full_name")
    @classmethod
    def _full_name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required.")
        return value

    @model_validator(mode="after")
    def _passwords_match(self) -> "SignupRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password must match.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return value.strip().lower()


class TrainingJobRequest(BaseModel):
    """`POST /api/training/jobs` (`docs/API.md`)."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: int
    target_column: str

    @field_validator("target_column")
    @classmethod
    def _target_column_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target_column is required.")
        return value


class ReportGenerateRequest(BaseModel):
    """`POST /api/reports/generate` (`docs/API.md`)."""

    model_config = ConfigDict(extra="ignore")

    report_type: str
    filters: dict[str, Any] = {}

    @field_validator("report_type")
    @classmethod
    def _report_type_known(cls, value: str) -> str:
        allowed = {"predictions_summary", "customers_summary"}
        if value not in allowed:
            raise ValueError(f"report_type must be one of {sorted(allowed)}.")
        return value


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return _validate_password_policy(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Password and confirm password must match.")
        return self
