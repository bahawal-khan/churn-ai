"""Flask application factory (`docs/BACKEND_SPEC.md` §1).

Phase 8: added the `auth` blueprint and the SQLAlchemy DB layer
(`backend/db/`) on top of Phase 7's `predictions`, `models`, and `health`
blueprints.

Phase 9: adds the remaining blueprints from `docs/BACKEND_SPEC.md` §2 —
`datasets`, `training`, `customers`, `analytics`, `reports` — completing the
route-group list. CORS and rate limiting (`docs/BACKEND_SPEC.md` §9) remain
out of scope here (deferred to Phase 11 Integration/Security hardening,
`docs/PROJECT_SPEC.md` §33) since neither is needed for route/service
correctness in a phase with no frontend calling cross-origin yet.
"""

from __future__ import annotations

import logging
import uuid

from flask import Flask, g

from backend.config import Config
from backend.db import session as db_session
from backend.errors import register_error_handlers
from backend.routes.analytics import analytics_bp
from backend.routes.auth import auth_bp
from backend.routes.customers import customers_bp
from backend.routes.datasets import datasets_bp
from backend.routes.health import health_bp
from backend.routes.models import models_bp
from backend.routes.predictions import predictions_bp
from backend.routes.reports import reports_bp
from backend.routes.training import training_bp


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.url_map.strict_slashes = False

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    @app.before_request
    def _assign_request_id() -> None:
        g.request_id = str(uuid.uuid4())

    register_error_handlers(app)
    db_session.init_app(app)

    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(models_bp, url_prefix="/api/models")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    app.register_blueprint(datasets_bp, url_prefix="/api/datasets")
    app.register_blueprint(training_bp, url_prefix="/api/training")
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
