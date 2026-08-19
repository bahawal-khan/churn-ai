"""Flask-Limiter setup (`docs/BACKEND_SPEC.md` §9, Phase 11).

A single shared `Limiter` instance, applied blueprint-wide to the three
route groups the spec calls out as rate-limit targets: auth (credential
stuffing), training, and prediction (resource exhaustion on free-tier
compute). Limit strings are read from `current_app.config` via a callable
rather than hardcoded, so they're configurable per environment
(`Config.RATE_LIMIT_*`) without a code change.
"""

from __future__ import annotations

from flask import current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def auth_rate_limit() -> str:
    return current_app.config["RATE_LIMIT_AUTH"]


def training_rate_limit() -> str:
    return current_app.config["RATE_LIMIT_TRAINING"]


def prediction_rate_limit() -> str:
    return current_app.config["RATE_LIMIT_PREDICTION"]
