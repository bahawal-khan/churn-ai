"""Flask application factory (`docs/BACKEND_SPEC.md` §1).

Phase 7 scope: `predictions`, `models`, and `health` blueprints only — no
`auth`, `datasets`, `training`, `customers`, `analytics`, or `reports`
blueprints yet, since those require the database/auth layers this phase
explicitly excludes (`docs/PROJECT_SPEC.md` phased plan).
"""

from __future__ import annotations

import logging
import uuid

from flask import Flask, g

from backend.config import Config
from backend.errors import register_error_handlers
from backend.routes.health import health_bp
from backend.routes.models import models_bp
from backend.routes.predictions import predictions_bp


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

    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(models_bp, url_prefix="/api/models")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
